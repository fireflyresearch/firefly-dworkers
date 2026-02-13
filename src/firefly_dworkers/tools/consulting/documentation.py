"""DocumentationTool — generate project documentation from structured inputs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec


class DocumentationTool(BaseTool):
    """Generate project documentation from structured inputs.

    Produces formatted documentation sections for various document types
    (project charter, SoW, technical spec, etc.).  This tool structures and
    organises information — it does not call external APIs.
    """

    def __init__(self, *, guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            "documentation",
            description="Generate project documentation from structured inputs",
            tags=["consulting", "documentation", "writing"],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="doc_type",
                    type_annotation="str",
                    description="Document type: charter, sow, technical_spec, meeting_notes, status_report",
                    required=True,
                ),
                ParameterSpec(
                    name="title",
                    type_annotation="str",
                    description="Document title",
                    required=True,
                ),
                ParameterSpec(
                    name="sections",
                    type_annotation="str",
                    description="Pipe-separated section contents (e.g. 'Overview|Scope|Timeline')",
                    required=True,
                ),
                ParameterSpec(
                    name="author",
                    type_annotation="str",
                    description="Document author",
                    required=False,
                    default="",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        doc_type = kwargs["doc_type"]
        title = kwargs["title"]
        sections_raw = kwargs["sections"]
        author = kwargs.get("author", "")

        section_list = [s.strip() for s in sections_raw.split("|") if s.strip()]

        # Template headers based on doc_type
        headers = self._get_section_headers(doc_type, len(section_list))

        # Build document
        lines = [f"# {title}", ""]
        if author:
            lines.append(f"**Author:** {author}")
            lines.append("")
        lines.append(f"**Document Type:** {doc_type.replace('_', ' ').title()}")
        lines.append("")

        for i, content in enumerate(section_list):
            header = headers[i] if i < len(headers) else f"Section {i + 1}"
            lines.append(f"## {header}")
            lines.append("")
            lines.append(content)
            lines.append("")

        document = "\n".join(lines)

        return {
            "document": document,
            "doc_type": doc_type,
            "title": title,
            "section_count": len(section_list),
            "format": "markdown",
        }

    def _get_section_headers(self, doc_type: str, count: int) -> list[str]:
        """Return default section headers for a given document type."""
        templates: dict[str, list[str]] = {
            "charter": ["Overview", "Objectives", "Scope", "Stakeholders", "Timeline", "Budget"],
            "sow": ["Introduction", "Scope of Work", "Deliverables", "Timeline", "Assumptions", "Acceptance Criteria"],
            "technical_spec": ["Overview", "Architecture", "Components", "Data Model", "API Design", "Security"],
            "meeting_notes": ["Attendees", "Agenda", "Discussion", "Action Items", "Next Steps"],
            "status_report": ["Summary", "Progress", "Risks & Issues", "Next Period Plan", "Metrics"],
        }
        default = [f"Section {i + 1}" for i in range(count)]
        return templates.get(doc_type, default)
