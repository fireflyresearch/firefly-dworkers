"""DocumentPipelineTool -- full pipeline from content brief to rendered DOCX/PDF.

Orchestrates:
1. Template analysis → DesignProfile
2. DesignEngine.design(brief, profile) → DesignSpec
3. Autonomy checkpoint: design_spec_approval
4. Image resolution
5. DesignSpec → SectionSpec conversion
6. Autonomy checkpoint: pre_render
7. Word or PDF rendering
8. Save to output_path
9. Autonomy checkpoint: deliverable
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

from firefly_dworkers.design.models import (
    ContentBrief,
    ContentSection,
    DataSeries,
    DataSet,
    ImageRequest,
    KeyMetric,
    OutputType,
    StyledTable,
)
from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.types import AutonomyLevel

logger = logging.getLogger(__name__)


def _sections_to_html(section_specs: list[Any]) -> str:
    """Convert a list of SectionSpecs to simple HTML for PDF rendering."""
    parts: list[str] = []
    for sec in section_specs:
        if sec.page_break_before:
            parts.append('<div style="page-break-before: always;"></div>')
        if sec.heading:
            level = min(sec.heading_level, 6)
            parts.append(f"<h{level}>{sec.heading}</h{level}>")
        if sec.content:
            parts.append(f"<p>{sec.content}</p>")
        for point in sec.bullet_points:
            parts.append(f"<li>{point}</li>")
        if sec.bullet_points:
            parts[-len(sec.bullet_points)] = "<ul>" + parts[-len(sec.bullet_points)]
            parts[-1] = parts[-1] + "</ul>"
        for item in sec.numbered_list:
            parts.append(f"<li>{item}</li>")
        if sec.numbered_list:
            parts[-len(sec.numbered_list)] = "<ol>" + parts[-len(sec.numbered_list)]
            parts[-1] = parts[-1] + "</ol>"
        if sec.callout:
            parts.append(f'<div class="callout">{sec.callout}</div>')
        if sec.table:
            parts.append(_table_to_html(sec.table))
    return "\n".join(parts)


def _table_to_html(table: Any) -> str:
    """Convert a TableData to an HTML table."""
    rows = ["<table>"]
    if table.headers:
        rows.append("<tr>" + "".join(f"<th>{h}</th>" for h in table.headers) + "</tr>")
    for row in table.rows:
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    rows.append("</table>")
    return "\n".join(rows)


@tool_registry.register("document_design_pipeline", category="document")
class DocumentPipelineTool(BaseTool):
    """Full design pipeline: content brief → DesignEngine → conversion → DOCX/PDF rendering."""

    def __init__(
        self,
        *,
        model: Any = "",
        vlm_model: str = "",
        autonomy_level: AutonomyLevel = AutonomyLevel.AUTONOMOUS,
        checkpoint_handler: Any = None,
        timeout: float = 300.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        params = [
            ParameterSpec(
                name="title",
                type_annotation="str",
                description="Document title.",
                required=True,
            ),
            ParameterSpec(
                name="sections",
                type_annotation="list",
                description="List of content section dicts with heading, content, bullet_points, etc.",
                required=True,
            ),
            ParameterSpec(
                name="template_path",
                type_annotation="str",
                description="Path to a DOCX template file for design extraction.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="output_path",
                type_annotation="str",
                description="Path to save the generated document.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="output_format",
                type_annotation="str",
                description="Output format: 'docx' or 'pdf'. Default: 'docx'.",
                required=False,
                default="docx",
            ),
            ParameterSpec(
                name="audience",
                type_annotation="str",
                description="Target audience for the document.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="tone",
                type_annotation="str",
                description="Desired tone (e.g. professional, casual, academic).",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="purpose",
                type_annotation="str",
                description="Purpose of the document.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="datasets",
                type_annotation="list",
                description="List of dataset dicts for chart generation.",
                required=False,
                default=[],
            ),
            ParameterSpec(
                name="image_requests",
                type_annotation="list",
                description="List of image request dicts (file, url, ai_generate, stock).",
                required=False,
                default=[],
            ),
            ParameterSpec(
                name="brand_colors",
                type_annotation="list",
                description="List of brand hex colors.",
                required=False,
                default=[],
            ),
            ParameterSpec(
                name="brand_fonts",
                type_annotation="list",
                description="List of brand font names.",
                required=False,
                default=[],
            ),
        ]

        super().__init__(
            "document_design_pipeline",
            description=(
                "Full design pipeline: content brief → DesignEngine → "
                "conversion → DOCX/PDF rendering. Produces professional "
                "documents from structured content."
            ),
            tags=["document", "design", "pipeline"],
            parameters=params,
            timeout=timeout,
            guards=guards,
        )

        self._model = model
        self._vlm_model = vlm_model
        self._autonomy_level = autonomy_level
        self._checkpoint_handler = checkpoint_handler
        self._last_artifact: bytes | None = None

    @property
    def artifact_bytes(self) -> bytes | None:
        """Bytes from the last pipeline execution, or ``None``."""
        return self._last_artifact

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the full document design pipeline."""
        # 1. Build ContentBrief from kwargs
        output_format = kwargs.get("output_format", "docx")
        brief = self._build_brief(kwargs, output_format=output_format)

        # 2. Analyze template → DesignProfile (if template_path provided)
        profile = None
        template_path = kwargs.get("template_path", "")
        if template_path:
            from firefly_dworkers.design.analyzer import TemplateAnalyzer

            analyzer = TemplateAnalyzer(vlm_model=self._vlm_model)
            profile = await analyzer.analyze(template_path)

        # 3. DesignEngine.design(brief, profile) → DesignSpec
        from firefly_dworkers.design.engine import DesignEngine

        engine = DesignEngine(self._model)
        spec = await engine.design(brief, profile)

        # 4. Checkpoint: design_spec_approval
        if not await self._maybe_checkpoint(
            "design_spec_approval",
            {
                "title": brief.title,
                "section_count": len(spec.document_sections),
                "chart_count": len(spec.charts),
            },
        ):
            return {"success": False, "reason": "Design spec rejected at checkpoint"}

        # 5. Resolve images (if any image_requests)
        if brief.image_requests:
            from firefly_dworkers.design.images import ImageResolver

            resolver = ImageResolver()
            spec.images = await resolver.resolve_all(brief.image_requests)

        # 6. Convert DesignSpec → list[SectionSpec]
        from firefly_dworkers.design.converter import convert_design_spec_to_section_specs

        section_specs = convert_design_spec_to_section_specs(spec)

        # 7. Checkpoint: pre_render
        if not await self._maybe_checkpoint(
            "pre_render",
            {"section_count": len(section_specs)},
        ):
            return {"success": False, "reason": "Pre-render rejected at checkpoint"}

        # 8. Render: WordTool or PDFTool based on output_format
        if output_format == "pdf":
            html_content = _sections_to_html(section_specs)
            if brief.title:
                html_content = f"<h1>{brief.title}</h1>\n{html_content}"
            pdf_tool = tool_registry.create("pdf")
            doc_bytes = await pdf_tool.generate(html_content, content_type="html")
        else:
            word_tool = tool_registry.create("word")
            doc_bytes = await word_tool.create(title=brief.title, sections=section_specs)

        self._last_artifact = doc_bytes

        # 9. Save to output_path if provided
        output_path = kwargs.get("output_path", "")
        if output_path:
            with open(output_path, "wb") as f:
                f.write(doc_bytes)
            output_path = os.path.abspath(output_path)

        # 10. Checkpoint: deliverable
        await self._maybe_checkpoint(
            "deliverable",
            {"output_path": output_path, "bytes_length": len(doc_bytes)},
        )

        result: dict[str, Any] = {
            "success": True,
            "section_count": len(section_specs),
            "bytes_length": len(doc_bytes),
            "output_format": output_format,
        }
        if output_path:
            result["output_path"] = output_path
        return result

    # -- Brief construction --------------------------------------------------

    @staticmethod
    def _build_brief(kwargs: dict[str, Any], *, output_format: str = "docx") -> ContentBrief:
        """Build a ContentBrief from tool kwargs."""
        output_type = OutputType.PDF if output_format == "pdf" else OutputType.DOCUMENT

        sections = []
        for s in kwargs.get("sections", []):
            if isinstance(s, ContentSection):
                sections.append(s)
            elif isinstance(s, dict):
                key_metrics = [
                    KeyMetric(**m) if isinstance(m, dict) else m
                    for m in s.get("key_metrics", [])
                ]
                table_data = None
                if s.get("table_data"):
                    td = s["table_data"]
                    table_data = StyledTable(**td) if isinstance(td, dict) else td

                sections.append(
                    ContentSection(
                        heading=s.get("heading", ""),
                        content=s.get("content", ""),
                        bullet_points=s.get("bullet_points", []),
                        key_metrics=key_metrics,
                        chart_ref=s.get("chart_ref", ""),
                        image_ref=s.get("image_ref", ""),
                        table_data=table_data,
                        emphasis=s.get("emphasis", "normal"),
                    )
                )

        datasets = []
        for ds in kwargs.get("datasets", []):
            if isinstance(ds, DataSet):
                datasets.append(ds)
            elif isinstance(ds, dict):
                series = [
                    DataSeries(**sr) if isinstance(sr, dict) else sr
                    for sr in ds.get("series", [])
                ]
                datasets.append(
                    DataSet(
                        name=ds.get("name", ""),
                        description=ds.get("description", ""),
                        categories=ds.get("categories", []),
                        series=series,
                        suggested_chart_type=ds.get("suggested_chart_type", ""),
                    )
                )

        image_requests = []
        for ir in kwargs.get("image_requests", []):
            if isinstance(ir, ImageRequest):
                image_requests.append(ir)
            elif isinstance(ir, dict):
                image_requests.append(ImageRequest(**ir))

        return ContentBrief(
            output_type=output_type,
            title=kwargs["title"],
            sections=sections,
            audience=kwargs.get("audience", ""),
            tone=kwargs.get("tone", ""),
            purpose=kwargs.get("purpose", ""),
            brand_colors=kwargs.get("brand_colors", []),
            brand_fonts=kwargs.get("brand_fonts", []),
            datasets=datasets,
            image_requests=image_requests,
        )

    # -- Checkpoint helper ---------------------------------------------------

    async def _maybe_checkpoint(
        self,
        checkpoint_type: str,
        deliverable: Any,
    ) -> bool:
        """Submit checkpoint if autonomy level requires it. Returns True if approved."""
        from firefly_dworkers.autonomy.levels import should_checkpoint

        if not should_checkpoint(self._autonomy_level, checkpoint_type):
            return True
        if self._checkpoint_handler is None:
            return True
        return await self._checkpoint_handler.on_checkpoint(
            "document_design_pipeline", checkpoint_type, deliverable
        )
