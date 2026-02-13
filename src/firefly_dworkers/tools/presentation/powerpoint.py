"""PowerPoint adapter for PresentationTool."""

from __future__ import annotations

import asyncio
import io
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.tools.presentation.base import PresentationTool
from firefly_dworkers.tools.presentation.models import (
    PlaceholderInfo,
    PresentationData,
    SlideData,
    SlideOperation,
    SlideSpec,
)
from firefly_dworkers.tools.registry import tool_registry

try:
    import pptx

    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False


def _require_pptx() -> None:
    if not PPTX_AVAILABLE:
        raise ImportError("python-pptx required: pip install firefly-dworkers[presentation]")


@tool_registry.register("powerpoint", category="presentation")
class PowerPointTool(PresentationTool):
    """Read, create, and modify PowerPoint presentations using python-pptx."""

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        super().__init__(
            "powerpoint",
            description="Read, create, and modify PowerPoint (.pptx) presentations.",
            timeout=timeout,
            guards=guards,
        )

    async def _read_presentation(self, source: str) -> PresentationData:
        _require_pptx()
        return await asyncio.to_thread(self._read_sync, source)

    async def _create_presentation(self, template: str, slides: list[SlideSpec]) -> bytes:
        _require_pptx()
        return await asyncio.to_thread(self._create_sync, template, slides)

    async def _modify_presentation(self, source: str, operations: list[SlideOperation]) -> bytes:
        _require_pptx()
        return await asyncio.to_thread(self._modify_sync, source, operations)

    # -- Sync implementations --

    def _read_sync(self, source: str) -> PresentationData:
        prs = pptx.Presentation(source)
        slides = []
        for i, slide in enumerate(prs.slides):
            title = ""
            content_parts: list[str] = []
            placeholders: list[PlaceholderInfo] = []

            for shape in slide.shapes:
                if shape.has_text_frame:
                    if shape.placeholder_format is not None and shape.placeholder_format.idx == 0:
                        title = shape.text_frame.text
                    else:
                        content_parts.append(shape.text_frame.text)

                if shape.placeholder_format is not None:
                    placeholders.append(
                        PlaceholderInfo(
                            idx=shape.placeholder_format.idx,
                            name=shape.name,
                        )
                    )

            notes = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text

            slides.append(
                SlideData(
                    index=i,
                    layout=slide.slide_layout.name,
                    title=title,
                    content="\n".join(content_parts),
                    placeholders=placeholders,
                    notes=notes,
                )
            )

        layouts = [layout.name for layout in prs.slide_layouts]
        return PresentationData(
            slides=slides,
            master_layouts=layouts,
            slide_width=prs.slide_width or 0,
            slide_height=prs.slide_height or 0,
        )

    def _create_sync(self, template: str, slides: list[SlideSpec]) -> bytes:
        prs = pptx.Presentation(template) if template else pptx.Presentation()

        for spec in slides:
            layout = self._find_layout(prs, spec.layout)
            slide = prs.slides.add_slide(layout)

            if slide.shapes.title and spec.title:
                slide.shapes.title.text = spec.title
                if spec.title_style:
                    self._apply_text_style(slide.shapes.title.text_frame, spec.title_style)

            body_ph = self._find_body_placeholder(slide)
            if body_ph:
                if spec.bullet_points:
                    tf = body_ph.text_frame
                    tf.clear()
                    for j, point in enumerate(spec.bullet_points):
                        if j == 0:
                            tf.text = point
                        else:
                            p = tf.add_paragraph()
                            p.text = point
                elif spec.content:
                    body_ph.text_frame.text = spec.content

                if spec.body_style:
                    self._apply_text_style(body_ph.text_frame, spec.body_style)

            if spec.table:
                self._add_table(slide, spec.table)

            if spec.chart:
                self._add_chart(slide, spec.chart)

            if spec.image_path:
                self._add_image(slide, spec.image_path)

            for img in spec.images:
                if img.file_path:
                    self._add_image_placement(slide, img)

            if spec.speaker_notes:
                slide.notes_slide.notes_text_frame.text = spec.speaker_notes

        buf = io.BytesIO()
        prs.save(buf)
        return buf.getvalue()

    def _modify_sync(self, source: str, operations: list[SlideOperation]) -> bytes:
        prs = pptx.Presentation(source)
        for op in operations:
            if op.operation == "update_content":
                slide = prs.slides[op.slide_index]
                if "title" in op.data and slide.shapes.title:
                    slide.shapes.title.text = op.data["title"]
            elif op.operation == "add_slide":
                layout = self._find_layout(prs, op.data.get("layout", "Blank"))
                prs.slides.add_slide(layout)

        buf = io.BytesIO()
        prs.save(buf)
        return buf.getvalue()

    # -- Helpers --

    @staticmethod
    def _find_layout(prs: Any, name: str) -> Any:
        for layout in prs.slide_layouts:
            if layout.name == name:
                return layout
        return prs.slide_layouts[0]

    @staticmethod
    def _find_body_placeholder(slide: Any) -> Any:
        for shape in slide.placeholders:
            if shape.placeholder_format.idx == 1:
                return shape
        return None

    @staticmethod
    def _add_table(slide: Any, table_spec: Any) -> None:
        from pptx.util import Inches

        if hasattr(table_spec, "headers"):
            headers = table_spec.headers
            rows_data = table_spec.rows
        else:
            headers = table_spec.get("headers", [])
            rows_data = table_spec.get("rows", [])

        n_rows = len(rows_data) + 1
        n_cols = len(headers)
        if n_cols == 0:
            return

        table_shape = slide.shapes.add_table(n_rows, n_cols, Inches(1), Inches(2), Inches(8), Inches(0.5 * n_rows))
        table = table_shape.table

        for i, header in enumerate(headers):
            table.cell(0, i).text = header

        for r, row in enumerate(rows_data):
            for c, val in enumerate(row):
                if c < n_cols:
                    table.cell(r + 1, c).text = str(val)

    @staticmethod
    def _add_chart(slide: Any, chart_spec: Any) -> None:
        """Add a native chart to a slide using ChartRenderer."""
        from firefly_dworkers.design.charts import ChartRenderer
        from firefly_dworkers.design.models import DataSeries, ResolvedChart

        renderer = ChartRenderer()
        resolved = ResolvedChart(
            chart_type=chart_spec.chart_type,
            title=chart_spec.title,
            categories=chart_spec.categories,
            series=[DataSeries(name=s["name"], values=s["values"]) for s in chart_spec.series],
            colors=chart_spec.colors,
            show_legend=chart_spec.show_legend,
            show_data_labels=chart_spec.show_data_labels,
            stacked=chart_spec.stacked,
        )
        renderer.render_for_pptx(resolved, slide)

    @staticmethod
    def _add_image(slide: Any, image_path: str) -> None:
        """Add a single image from a file path to a slide."""
        from pptx.util import Inches

        slide.shapes.add_picture(image_path, Inches(1), Inches(2), Inches(4), Inches(3))

    @staticmethod
    def _add_image_placement(slide: Any, img: Any) -> None:
        """Add an image with explicit placement from an ImagePlacement spec."""
        from pptx.util import Emu, Inches

        slide.shapes.add_picture(
            img.file_path,
            Emu(int(img.left)) if img.left else Inches(1),
            Emu(int(img.top)) if img.top else Inches(2),
            Emu(int(img.width)) if img.width else None,
            Emu(int(img.height)) if img.height else None,
        )

    @staticmethod
    def _apply_text_style(text_frame: Any, style: Any) -> None:
        """Apply TextStyle to all runs in a text frame."""
        from pptx.dml.color import RGBColor
        from pptx.util import Pt

        if style is None:
            return
        for paragraph in text_frame.paragraphs:
            for run in paragraph.runs:
                if style.font_name:
                    run.font.name = style.font_name
                if style.font_size > 0:
                    run.font.size = Pt(style.font_size)
                if style.bold:
                    run.font.bold = True
                if style.italic:
                    run.font.italic = True
                if style.color:
                    hex_color = style.color.lstrip("#")
                    run.font.color.rgb = RGBColor(
                        int(hex_color[0:2], 16),
                        int(hex_color[2:4], 16),
                        int(hex_color[4:6], 16),
                    )
