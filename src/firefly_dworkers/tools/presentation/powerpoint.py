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
                    placeholders.append(PlaceholderInfo(
                        idx=shape.placeholder_format.idx,
                        name=shape.name,
                    ))

            notes = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text

            slides.append(SlideData(
                index=i,
                layout=slide.slide_layout.name,
                title=title,
                content="\n".join(content_parts),
                placeholders=placeholders,
                notes=notes,
            ))

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

            if spec.table:
                self._add_table(slide, spec.table)

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

        table_shape = slide.shapes.add_table(
            n_rows, n_cols, Inches(1), Inches(2), Inches(8), Inches(0.5 * n_rows)
        )
        table = table_shape.table

        for i, header in enumerate(headers):
            table.cell(0, i).text = header

        for r, row in enumerate(rows_data):
            for c, val in enumerate(row):
                if c < n_cols:
                    table.cell(r + 1, c).text = str(val)
