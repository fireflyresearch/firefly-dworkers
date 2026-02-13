"""DocumentationTool — generate project documentation from structured inputs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol, ParameterSpec

from firefly_dworkers.tools.consulting.base import ConsultingTool
from firefly_dworkers.tools.registry import tool_registry

_DEFAULT_TEMPLATES: dict[str, list[str]] = {
    "charter": ["Overview", "Objectives", "Scope", "Stakeholders", "Timeline", "Budget"],
    "sow": ["Introduction", "Scope of Work", "Deliverables", "Timeline", "Assumptions", "Acceptance Criteria"],
    "technical_spec": ["Overview", "Architecture", "Components", "Data Model", "API Design", "Security"],
    "meeting_notes": ["Attendees", "Agenda", "Discussion", "Action Items", "Next Steps"],
    "status_report": ["Summary", "Progress", "Risks & Issues", "Next Period Plan", "Metrics"],
}


@tool_registry.register("documentation", category="consulting")
class DocumentationTool(ConsultingTool):
    """Generate project documentation from structured inputs.

    Produces formatted documentation sections for various document types
    (project charter, SoW, technical spec, etc.).  This tool structures and
    organises information — it does not call external APIs.

    Configuration parameters:

    * ``section_templates`` -- Dict mapping document types to ordered lists of
      section header names.  Merged with built-in templates (custom entries take
      precedence).
    * ``section_separator`` -- Character used to split the ``sections``
      parameter string (default ``|``).
    * ``default_author`` -- Fallback author when not specified at call time.
    * ``heading_level`` -- Markdown heading level for section headers (1-6).
    """

    def __init__(
        self,
        *,
        section_templates: dict[str, list[str]] | None = None,
        section_separator: str = "|",
        default_author: str = "",
        heading_level: int = 2,
        guards: Sequence[GuardProtocol] = (),
    ):
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
                    description=f"'{section_separator}'-separated section contents",
                    required=True,
                ),
                ParameterSpec(
                    name="author",
                    type_annotation="str",
                    description="Document author",
                    required=False,
                    default=default_author,
                ),
            ],
        )
        # Merge built-in templates with any custom overrides
        self._templates: dict[str, list[str]] = {**_DEFAULT_TEMPLATES}
        if section_templates:
            self._templates.update(section_templates)
        self._separator = section_separator
        self._default_author = default_author
        self._heading_level = max(1, min(6, heading_level))

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        doc_type = kwargs["doc_type"]
        title = kwargs["title"]
        sections_raw = kwargs["sections"]
        author = kwargs.get("author", self._default_author)

        section_list = [s.strip() for s in sections_raw.split(self._separator) if s.strip()]

        # Template headers based on doc_type
        headers = self._get_section_headers(doc_type, len(section_list))

        section_prefix = "#" * self._heading_level

        # Build document
        lines = [f"# {title}", ""]
        if author:
            lines.append(f"**Author:** {author}")
            lines.append("")
        lines.append(f"**Document Type:** {doc_type.replace('_', ' ').title()}")
        lines.append("")

        for i, content in enumerate(section_list):
            header = headers[i] if i < len(headers) else f"Section {i + 1}"
            lines.append(f"{section_prefix} {header}")
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
        """Return section headers for a given document type."""
        default = [f"Section {i + 1}" for i in range(count)]
        return self._templates.get(doc_type, default)
