"""DesignEngine -- LLM-powered creative brain for document design.

Takes a :class:`ContentBrief` and an optional :class:`DesignProfile` and
produces a complete :class:`DesignSpec` that downstream tools can render.

Three main responsibilities:

1. **Autonomous profile generation** -- when no reference template is
   provided, uses the LLM to generate a :class:`DesignProfile` based on
   content context (audience, tone, purpose).
2. **Chart type selection** -- analyzes each :class:`DataSet` and selects
   the optimal chart type using heuristics (no LLM call needed).
3. **Layout design** -- uses the LLM to decide slide/section/sheet
   structure, layout selection, and content distribution.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic_ai import Agent

from firefly_dworkers.design.models import (
    ContentBrief,
    DataSeries,
    DataSet,
    DesignProfile,
    DesignSpec,
    OutputType,
    ResolvedChart,
)


# ── Date/time pattern for heuristic chart-type selection ─────────────────

_DATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\d{4}[-/]\d{2}([-/]\d{2})?$"),  # 2024-01, 2024-01-15
    re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$"),  # 1/15/2024
    re.compile(
        r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
        re.IGNORECASE,
    ),  # Jan, January, Jan 2024
    re.compile(r"^Q[1-4]\b", re.IGNORECASE),  # Q1, Q2 2024
    re.compile(r"^\d{4}$"),  # 2024 (year only)
    re.compile(
        r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)",
        re.IGNORECASE,
    ),  # Day names
    re.compile(r"^Week\s+\d+", re.IGNORECASE),  # Week 1, Week 12
]


def _looks_like_date(value: str) -> bool:
    """Return True if *value* matches a common date/time pattern."""
    return any(p.search(value) for p in _DATE_PATTERNS)


def _categories_are_temporal(categories: list[str]) -> bool:
    """Return True if most categories look like dates or time periods."""
    if not categories:
        return False
    matches = sum(1 for c in categories if _looks_like_date(c))
    return matches / len(categories) >= 0.5


def _series_are_all_numeric(series: list[DataSeries]) -> bool:
    """Return True if every value in every series is numeric."""
    for s in series:
        for v in s.values:
            if not isinstance(v, (int, float)):
                return False
    return True


# ── DesignEngine ─────────────────────────────────────────────────────────


class DesignEngine:
    """LLM-powered creative reasoning engine for document design.

    Parameters:
        model: A model string (e.g. ``"openai:gpt-4o"``) or a pydantic-ai
            :class:`Model` instance (including :class:`TestModel`).  When
            an empty string is passed, the Agent will use its default model.
        tenant_config: Optional tenant configuration for context.
    """

    def __init__(
        self,
        model: Any = "",
        tenant_config: Any | None = None,
    ) -> None:
        self._model = model
        self._config = tenant_config

    # ── Public API ──────────────────────────────────────────────────────

    async def design(
        self,
        brief: ContentBrief,
        profile: DesignProfile | None = None,
    ) -> DesignSpec:
        """Produce a complete :class:`DesignSpec` from a content brief.

        1. If *profile* is ``None``, generate one autonomously via the LLM.
        2. Resolve chart types for every dataset (heuristic, no LLM).
        3. Design the layout structure via the LLM.
        4. Merge charts into the final spec and return.
        """
        if profile is None:
            profile = await self._generate_autonomous_profile(brief)

        charts = self._resolve_chart_types(brief.datasets, profile)
        spec = await self._design_layout(brief, profile)

        # Ensure the spec carries the correct output_type and profile,
        # regardless of what the LLM returned.
        spec.output_type = brief.output_type
        spec.profile = profile
        spec.charts = charts
        return spec

    # ── Autonomous profile generation (LLM) ────────────────────────────

    async def _generate_autonomous_profile(
        self,
        brief: ContentBrief,
    ) -> DesignProfile:
        """Use the LLM to generate a DesignProfile from content context."""
        agent: Agent[None, DesignProfile] = Agent(
            self._model or "test",
            output_type=DesignProfile,
            system_prompt=(
                "You are a professional graphic designer. Based on the "
                "content brief provided, choose an appropriate design "
                "profile including colors, fonts, and styles.\n\n"
                "Consider the audience, tone, and purpose when making "
                "design decisions. For corporate audiences use professional "
                "blues and grays; for creative work use vibrant palettes; "
                "for academic content use classic serif fonts.\n\n"
                "Return a complete DesignProfile with:\n"
                "- primary_color, secondary_color, accent_color (hex)\n"
                "- background_color, text_color (hex)\n"
                "- color_palette (list of hex colors)\n"
                "- heading_font, body_font\n"
                "- font_sizes (dict with 'h1', 'h2', 'body' keys)\n"
                "- line_spacing"
            ),
        )

        prompt = self._build_profile_prompt(brief)
        result = await agent.run(prompt)
        return result.output

    @staticmethod
    def _build_profile_prompt(brief: ContentBrief) -> str:
        """Build a user prompt for autonomous profile generation."""
        parts: list[str] = [
            f"Title: {brief.title}",
            f"Output type: {brief.output_type.value}",
        ]
        if brief.audience:
            parts.append(f"Audience: {brief.audience}")
        if brief.tone:
            parts.append(f"Tone: {brief.tone}")
        if brief.purpose:
            parts.append(f"Purpose: {brief.purpose}")
        if brief.brand_colors:
            parts.append(f"Brand colors: {', '.join(brief.brand_colors)}")
        if brief.brand_fonts:
            parts.append(f"Brand fonts: {', '.join(brief.brand_fonts)}")
        if brief.sections:
            headings = [s.heading for s in brief.sections if s.heading]
            if headings:
                parts.append(f"Section headings: {', '.join(headings)}")
        return "\n".join(parts)

    # ── Chart type selection (heuristic, no LLM) ───────────────────────

    def _resolve_chart_types(
        self,
        datasets: list[DataSet],
        profile: DesignProfile,
    ) -> dict[str, ResolvedChart]:
        """Select the best chart type for each dataset using heuristics.

        Rules (in priority order):
        1. Use ``dataset.suggested_chart_type`` if provided.
        2. Time-series categories -> line chart.
        3. Single series with <= 6 categories -> pie chart.
        4. Two numeric columns (2 series, no categories) -> scatter.
        5. Multiple series -> grouped bar chart.
        6. Default -> bar chart.
        """
        charts: dict[str, ResolvedChart] = {}

        for ds in datasets:
            chart_type = self._select_chart_type(ds)
            colors = list(profile.color_palette) if profile.color_palette else []

            charts[ds.name] = ResolvedChart(
                chart_type=chart_type,
                title=ds.description or ds.name,
                categories=list(ds.categories),
                series=[DataSeries(name=s.name, values=list(s.values)) for s in ds.series],
                colors=colors,
            )

        return charts

    @staticmethod
    def _select_chart_type(ds: DataSet) -> str:
        """Pick the best chart type for a single dataset."""
        # Honour explicit suggestion
        if ds.suggested_chart_type:
            return ds.suggested_chart_type

        n_series = len(ds.series)
        n_categories = len(ds.categories)

        # Time-series detection
        if _categories_are_temporal(ds.categories):
            return "line"

        # Single series with few categories -> pie
        if n_series == 1 and 0 < n_categories <= 6:
            return "pie"

        # Two numeric series with no categories -> scatter
        if n_series == 2 and n_categories == 0 and _series_are_all_numeric(ds.series):
            return "scatter"

        # Multiple series -> grouped bar
        if n_series > 1:
            return "bar"

        # Default
        return "bar"

    # ── Layout design (LLM) ────────────────────────────────────────────

    async def _design_layout(
        self,
        brief: ContentBrief,
        profile: DesignProfile,
    ) -> DesignSpec:
        """Use the LLM to create the full layout structure."""
        agent: Agent[None, DesignSpec] = Agent(
            self._model or "test",
            output_type=DesignSpec,
            system_prompt=self._build_layout_system_prompt(brief.output_type),
        )

        prompt = self._build_layout_prompt(brief, profile)
        result = await agent.run(prompt)
        return result.output

    @staticmethod
    def _build_layout_system_prompt(output_type: OutputType) -> str:
        """Build the system prompt for layout design based on output type."""
        base = (
            "You are a professional document layout designer. "
            "Create a complete DesignSpec for the given content brief.\n\n"
        )

        type_instructions = {
            OutputType.PRESENTATION: (
                "This is a PRESENTATION. Populate the 'slides' field with "
                "SlideDesign objects. Create a title slide first, then one "
                "slide per content section. Choose appropriate layouts like "
                "'Title Slide', 'Title and Content', 'Two Content', "
                "'Section Header', etc. Distribute content blocks, charts, "
                "and images across slides logically."
            ),
            OutputType.DOCUMENT: (
                "This is a DOCUMENT. Populate the 'document_sections' field "
                "with SectionDesign objects. Create sections with appropriate "
                "heading levels, content blocks, and page breaks. Use "
                "heading_level 1 for main sections, 2 for subsections."
            ),
            OutputType.SPREADSHEET: (
                "This is a SPREADSHEET. Populate the 'sheets' field with "
                "SheetDesign objects. Create sheets with appropriate headers, "
                "column widths, and number formats. Group related data on "
                "the same sheet."
            ),
            OutputType.PDF: (
                "This is a PDF document. Populate the 'document_sections' "
                "field with SectionDesign objects. Structure it like a "
                "document with clear sections, headings, and content blocks."
            ),
        }

        return base + type_instructions.get(output_type, type_instructions[OutputType.DOCUMENT])

    @staticmethod
    def _build_layout_prompt(brief: ContentBrief, profile: DesignProfile) -> str:
        """Build the user prompt for layout design."""
        parts: list[str] = [
            f"Title: {brief.title}",
            f"Output type: {brief.output_type.value}",
            f"Number of content sections: {len(brief.sections)}",
        ]

        if brief.audience:
            parts.append(f"Audience: {brief.audience}")
        if brief.purpose:
            parts.append(f"Purpose: {brief.purpose}")

        for i, section in enumerate(brief.sections, 1):
            section_parts = [f"\nSection {i}:"]
            if section.heading:
                section_parts.append(f"  Heading: {section.heading}")
            if section.content:
                section_parts.append(f"  Content: {section.content[:200]}")
            if section.bullet_points:
                section_parts.append(f"  Bullets: {len(section.bullet_points)} items")
            if section.key_metrics:
                section_parts.append(f"  Metrics: {len(section.key_metrics)} KPIs")
            if section.chart_ref:
                section_parts.append(f"  Chart: {section.chart_ref}")
            if section.image_ref:
                section_parts.append(f"  Image: {section.image_ref}")
            if section.table_data:
                section_parts.append("  Has table data")
            parts.extend(section_parts)

        if brief.datasets:
            parts.append(f"\nDatasets: {len(brief.datasets)}")
            for ds in brief.datasets:
                parts.append(f"  - {ds.name}: {ds.description or 'no description'}")

        if profile.heading_font:
            parts.append(f"\nDesign profile heading font: {profile.heading_font}")
        if profile.primary_color:
            parts.append(f"Primary color: {profile.primary_color}")

        return "\n".join(parts)
