"""ReportGenerationTool — generate structured report sections."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec


class ReportGenerationTool(BaseTool):
    """Generate structured report sections from data and analysis results.

    Supports markdown, plain text, and JSON output formats.
    This tool structures and organises information — it does not call external
    APIs.
    """

    def __init__(self, *, guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            "report_generation",
            description="Generate structured report sections from data and analysis results",
            tags=["consulting", "reporting", "documentation"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="title",
                    type_annotation="str",
                    description="Report section title",
                    required=True,
                ),
                ParameterSpec(
                    name="data",
                    type_annotation="str",
                    description="Data/analysis to include in the report",
                    required=True,
                ),
                ParameterSpec(
                    name="format",
                    type_annotation="str",
                    description="Output format: markdown, text, or json",
                    required=False,
                    default="markdown",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        title = kwargs["title"]
        data = kwargs["data"]
        fmt = kwargs.get("format", "markdown")

        if fmt == "markdown":
            return {"content": f"## {title}\n\n{data}\n", "format": "markdown"}
        if fmt == "json":
            return {"content": {"title": title, "body": data}, "format": "json"}
        return {"content": f"{title}\n{'=' * len(title)}\n\n{data}\n", "format": "text"}
