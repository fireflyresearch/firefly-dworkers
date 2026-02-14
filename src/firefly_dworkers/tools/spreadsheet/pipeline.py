"""SpreadsheetPipelineTool -- full pipeline from content brief to rendered XLSX.

Orchestrates:
1. Template analysis → DesignProfile
2. DesignEngine.design(brief, profile) → DesignSpec
3. Autonomy checkpoint: design_spec_approval
4. DesignSpec → SheetSpec conversion
5. Autonomy checkpoint: pre_render
6. Excel rendering
7. Save to output_path
8. Autonomy checkpoint: deliverable
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


@tool_registry.register("spreadsheet_design_pipeline", category="spreadsheet")
class SpreadsheetPipelineTool(BaseTool):
    """Full design pipeline: content brief → DesignEngine → conversion → XLSX rendering."""

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
                description="Spreadsheet title (used in content brief).",
                required=True,
            ),
            ParameterSpec(
                name="sections",
                type_annotation="list",
                description="List of content section dicts with heading, content, etc.",
                required=True,
            ),
            ParameterSpec(
                name="template_path",
                type_annotation="str",
                description="Path to an XLSX template file for design extraction.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="output_path",
                type_annotation="str",
                description="Path to save the generated XLSX file.",
                required=False,
                default="",
            ),
            ParameterSpec(
                name="audience",
                type_annotation="str",
                description="Target audience for the spreadsheet.",
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
                description="Purpose of the spreadsheet.",
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
            "spreadsheet_design_pipeline",
            description=(
                "Full design pipeline: content brief → DesignEngine → "
                "conversion → XLSX rendering. Produces professional "
                "spreadsheets from structured content."
            ),
            tags=["spreadsheet", "design", "pipeline"],
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
        """Execute the full spreadsheet design pipeline."""
        # 1. Build ContentBrief from kwargs
        brief = self._build_brief(kwargs)

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
                "sheet_count": len(spec.sheets),
                "chart_count": len(spec.charts),
            },
        ):
            return {"success": False, "reason": "Design spec rejected at checkpoint"}

        # 5. Convert DesignSpec → list[SheetSpec]
        from firefly_dworkers.design.converter import convert_design_spec_to_sheet_specs

        sheet_specs = convert_design_spec_to_sheet_specs(spec)

        # 6. Checkpoint: pre_render
        if not await self._maybe_checkpoint(
            "pre_render",
            {"sheet_count": len(sheet_specs)},
        ):
            return {"success": False, "reason": "Pre-render rejected at checkpoint"}

        # 7. ExcelTool().create(sheets=sheet_specs) → bytes
        excel_tool = tool_registry.create("excel")
        xlsx_bytes = await excel_tool.create(sheets=sheet_specs)

        self._last_artifact = xlsx_bytes

        # 8. Save to output_path if provided
        output_path = kwargs.get("output_path", "")
        if output_path:
            with open(output_path, "wb") as f:
                f.write(xlsx_bytes)
            output_path = os.path.abspath(output_path)

        # 9. Checkpoint: deliverable
        await self._maybe_checkpoint(
            "deliverable",
            {"output_path": output_path, "bytes_length": len(xlsx_bytes)},
        )

        result: dict[str, Any] = {
            "success": True,
            "sheet_count": len(sheet_specs),
            "bytes_length": len(xlsx_bytes),
        }
        if output_path:
            result["output_path"] = output_path
        return result

    # -- Brief construction --------------------------------------------------

    @staticmethod
    def _build_brief(kwargs: dict[str, Any]) -> ContentBrief:
        """Build a ContentBrief from tool kwargs."""
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
            output_type=OutputType.SPREADSHEET,
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
            "spreadsheet_design_pipeline", checkpoint_type, deliverable
        )
