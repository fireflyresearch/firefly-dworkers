"""UnifiedDesignPipeline -- single entry point that dispatches to format-specific pipelines.

Routes ``output_type`` to the correct pipeline tool:
- ``"presentation"`` → ``DesignPipelineTool``  (``design_pipeline``)
- ``"document"``     → ``DocumentPipelineTool`` (``document_design_pipeline``)
- ``"spreadsheet"``  → ``SpreadsheetPipelineTool`` (``spreadsheet_design_pipeline``)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.types import AutonomyLevel

_DISPATCH: dict[str, str] = {
    "presentation": "design_pipeline",
    "document": "document_design_pipeline",
    "spreadsheet": "spreadsheet_design_pipeline",
}


@tool_registry.register("unified_design_pipeline", category="design")
class UnifiedDesignPipeline(BaseTool):
    """Unified design pipeline that dispatches to format-specific pipelines."""

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
                name="output_type",
                type_annotation="str",
                description="Output format: 'presentation', 'document', or 'spreadsheet'.",
                required=True,
            ),
            ParameterSpec(
                name="title",
                type_annotation="str",
                description="Title for the output artifact.",
                required=True,
            ),
            ParameterSpec(
                name="sections",
                type_annotation="list",
                description="List of content section dicts.",
                required=True,
            ),
        ]
        super().__init__(
            "unified_design_pipeline",
            description=(
                "Unified design pipeline that dispatches to format-specific "
                "pipelines (presentation, document, spreadsheet)."
            ),
            tags=["design", "pipeline", "unified"],
            parameters=params,
            timeout=timeout,
            guards=guards,
        )
        self._init_kwargs = {
            "model": model,
            "vlm_model": vlm_model,
            "autonomy_level": autonomy_level,
            "checkpoint_handler": checkpoint_handler,
        }

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        output_type = kwargs.get("output_type", "presentation")

        tool_name = _DISPATCH.get(output_type)
        if not tool_name or not tool_registry.has(tool_name):
            raise ValueError(
                f"No pipeline for output_type={output_type!r}. "
                f"Supported: {list(_DISPATCH.keys())}"
            )

        pipeline = tool_registry.create(tool_name, **self._init_kwargs)
        return await pipeline._execute(**kwargs)
