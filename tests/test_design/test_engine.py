"""Tests for DesignEngine -- LLM-powered creative reasoning engine."""

from __future__ import annotations

from pydantic_ai.models.test import TestModel

from firefly_dworkers.design.engine import (
    DesignEngine,
    _categories_are_temporal,
    _looks_like_date,
)
from firefly_dworkers.design.models import (
    ContentBrief,
    ContentSection,
    DataSeries,
    DataSet,
    DesignProfile,
    DesignSpec,
    OutputType,
    ResolvedChart,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_brief(
    output_type: OutputType = OutputType.PRESENTATION,
    **kwargs: object,
) -> ContentBrief:
    defaults: dict[str, object] = {
        "output_type": output_type,
        "title": "Test Deck",
        "sections": [ContentSection(heading="Intro", content="Hello")],
    }
    defaults.update(kwargs)
    return ContentBrief(**defaults)  # type: ignore[arg-type]


def _make_profile(**kwargs: object) -> DesignProfile:
    defaults: dict[str, object] = {
        "primary_color": "#003366",
        "secondary_color": "#336699",
        "accent_color": "#ff6600",
        "heading_font": "Arial",
        "body_font": "Calibri",
        "color_palette": ["#003366", "#336699", "#ff6600"],
    }
    defaults.update(kwargs)
    return DesignProfile(**defaults)  # type: ignore[arg-type]


def _make_engine() -> DesignEngine:
    return DesignEngine(model=TestModel())


# ── DesignEngine.design() ────────────────────────────────────────────────


class TestDesignEngineFull:
    """Integration tests for the full design() pipeline."""

    async def test_design_presentation_returns_spec(self) -> None:
        engine = _make_engine()
        brief = _make_brief(output_type=OutputType.PRESENTATION)
        spec = await engine.design(brief)

        assert isinstance(spec, DesignSpec)
        assert spec.output_type == OutputType.PRESENTATION

    async def test_design_document_returns_spec(self) -> None:
        engine = _make_engine()
        brief = _make_brief(output_type=OutputType.DOCUMENT)
        spec = await engine.design(brief)

        assert isinstance(spec, DesignSpec)
        assert spec.output_type == OutputType.DOCUMENT

    async def test_design_spreadsheet_returns_spec(self) -> None:
        engine = _make_engine()
        brief = _make_brief(output_type=OutputType.SPREADSHEET)
        spec = await engine.design(brief)

        assert isinstance(spec, DesignSpec)
        assert spec.output_type == OutputType.SPREADSHEET

    async def test_design_pdf_returns_spec(self) -> None:
        engine = _make_engine()
        brief = _make_brief(output_type=OutputType.PDF)
        spec = await engine.design(brief)

        assert isinstance(spec, DesignSpec)
        assert spec.output_type == OutputType.PDF

    async def test_design_with_explicit_profile(self) -> None:
        engine = _make_engine()
        profile = _make_profile()
        brief = _make_brief()
        spec = await engine.design(brief, profile=profile)

        assert spec.profile is profile
        assert spec.profile.primary_color == "#003366"

    async def test_design_without_profile_generates_one(self) -> None:
        engine = _make_engine()
        brief = _make_brief()
        spec = await engine.design(brief)

        assert isinstance(spec.profile, DesignProfile)

    async def test_design_includes_charts_from_datasets(self) -> None:
        engine = _make_engine()
        profile = _make_profile()
        datasets = [
            DataSet(
                name="revenue",
                categories=["Q1", "Q2", "Q3"],
                series=[DataSeries(name="2025", values=[100, 200, 300])],
            ),
        ]
        brief = _make_brief(datasets=datasets)
        spec = await engine.design(brief, profile=profile)

        assert "revenue" in spec.charts
        assert isinstance(spec.charts["revenue"], ResolvedChart)

    async def test_design_output_type_matches_brief(self) -> None:
        """output_type on the spec must always match the brief."""
        engine = _make_engine()
        for ot in OutputType:
            brief = _make_brief(output_type=ot)
            spec = await engine.design(brief, profile=_make_profile())
            assert spec.output_type == ot

    async def test_design_with_rich_brief(self) -> None:
        engine = _make_engine()
        brief = ContentBrief(
            output_type=OutputType.PRESENTATION,
            title="Q1 Business Review",
            audience="C-suite executives",
            tone="professional",
            purpose="Quarterly business review",
            sections=[
                ContentSection(heading="Executive Summary", content="Overview of Q1"),
                ContentSection(heading="Revenue", content="Revenue grew 15%"),
                ContentSection(heading="Outlook", content="Strong pipeline"),
            ],
            datasets=[
                DataSet(
                    name="quarterly_revenue",
                    description="Revenue by quarter",
                    categories=["Q1", "Q2", "Q3", "Q4"],
                    series=[DataSeries(name="Revenue", values=[100, 120, 130, 150])],
                ),
            ],
            brand_colors=["#003366", "#ff6600"],
            brand_fonts=["Helvetica", "Georgia"],
        )
        spec = await engine.design(brief)

        assert isinstance(spec, DesignSpec)
        assert spec.output_type == OutputType.PRESENTATION
        assert "quarterly_revenue" in spec.charts


# ── Autonomous profile generation ────────────────────────────────────────


class TestAutonomousProfile:
    """Tests for _generate_autonomous_profile."""

    async def test_generates_design_profile(self) -> None:
        engine = _make_engine()
        brief = _make_brief(audience="investors", tone="formal")
        profile = await engine._generate_autonomous_profile(brief)

        assert isinstance(profile, DesignProfile)

    async def test_profile_prompt_includes_audience(self) -> None:
        brief = _make_brief(audience="students")
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "students" in prompt

    async def test_profile_prompt_includes_tone(self) -> None:
        brief = _make_brief(tone="casual")
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "casual" in prompt

    async def test_profile_prompt_includes_purpose(self) -> None:
        brief = _make_brief(purpose="training")
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "training" in prompt

    async def test_profile_prompt_includes_title(self) -> None:
        brief = _make_brief(title="My Report")
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "My Report" in prompt

    async def test_profile_prompt_includes_output_type(self) -> None:
        brief = _make_brief(output_type=OutputType.SPREADSHEET)
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "spreadsheet" in prompt

    async def test_profile_prompt_includes_brand_colors(self) -> None:
        brief = _make_brief(brand_colors=["#ff0000", "#00ff00"])
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "#ff0000" in prompt
        assert "#00ff00" in prompt

    async def test_profile_prompt_includes_brand_fonts(self) -> None:
        brief = _make_brief(brand_fonts=["Helvetica", "Georgia"])
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "Helvetica" in prompt
        assert "Georgia" in prompt

    async def test_profile_prompt_includes_section_headings(self) -> None:
        brief = _make_brief(
            sections=[
                ContentSection(heading="Introduction"),
                ContentSection(heading="Methodology"),
            ],
        )
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "Introduction" in prompt
        assert "Methodology" in prompt

    async def test_profile_prompt_omits_empty_fields(self) -> None:
        brief = _make_brief(audience="", tone="", purpose="")
        prompt = DesignEngine._build_profile_prompt(brief)
        assert "Audience" not in prompt
        assert "Tone" not in prompt
        assert "Purpose" not in prompt


# ── Chart type selection (heuristics) ────────────────────────────────────


class TestChartTypeSelection:
    """Tests for _resolve_chart_types and _select_chart_type heuristics."""

    async def test_suggested_chart_type_honored(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="test",
            categories=["A", "B", "C"],
            series=[DataSeries(name="S1", values=[1, 2, 3])],
            suggested_chart_type="doughnut",
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["test"].chart_type == "doughnut"

    async def test_temporal_categories_produce_line(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="trend",
            categories=["Jan 2024", "Feb 2024", "Mar 2024"],
            series=[DataSeries(name="Sales", values=[100, 120, 140])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["trend"].chart_type == "line"

    async def test_quarter_categories_produce_line(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="quarterly",
            categories=["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"],
            series=[DataSeries(name="Revenue", values=[100, 120, 130, 150])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["quarterly"].chart_type == "line"

    async def test_year_categories_produce_line(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="yearly",
            categories=["2020", "2021", "2022", "2023"],
            series=[DataSeries(name="Growth", values=[5, 7, 6, 8])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["yearly"].chart_type == "line"

    async def test_single_series_few_categories_produce_pie(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="share",
            categories=["Product A", "Product B", "Product C"],
            series=[DataSeries(name="Share", values=[40, 35, 25])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["share"].chart_type == "pie"

    async def test_single_series_six_categories_produce_pie(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="share",
            categories=["A", "B", "C", "D", "E", "F"],
            series=[DataSeries(name="Share", values=[20, 15, 15, 20, 15, 15])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["share"].chart_type == "pie"

    async def test_single_series_seven_categories_produce_bar(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="many",
            categories=["A", "B", "C", "D", "E", "F", "G"],
            series=[DataSeries(name="Count", values=[1, 2, 3, 4, 5, 6, 7])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["many"].chart_type == "bar"

    async def test_two_numeric_series_no_categories_produce_scatter(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="correlation",
            categories=[],
            series=[
                DataSeries(name="X", values=[1, 2, 3, 4]),
                DataSeries(name="Y", values=[2, 4, 5, 8]),
            ],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["correlation"].chart_type == "scatter"

    async def test_multiple_series_produce_bar(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="comparison",
            categories=["East", "West", "North"],
            series=[
                DataSeries(name="2024", values=[100, 200, 150]),
                DataSeries(name="2025", values=[120, 220, 170]),
            ],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["comparison"].chart_type == "bar"

    async def test_default_produces_bar(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="default",
            categories=["A", "B", "C", "D", "E", "F", "G", "H"],
            series=[DataSeries(name="Counts", values=[1, 2, 3, 4, 5, 6, 7, 8])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["default"].chart_type == "bar"

    async def test_empty_datasets_returns_empty_dict(self) -> None:
        engine = _make_engine()
        charts = await engine._resolve_chart_types([], _make_profile())
        assert charts == {}

    async def test_multiple_datasets_all_resolved(self) -> None:
        engine = _make_engine()
        datasets = [
            DataSet(
                name="ds1",
                categories=["A", "B"],
                series=[DataSeries(name="S1", values=[10, 20])],
            ),
            DataSet(
                name="ds2",
                categories=["Jan", "Feb", "Mar"],
                series=[DataSeries(name="S2", values=[1, 2, 3])],
            ),
        ]
        charts = await engine._resolve_chart_types(datasets, _make_profile())
        assert "ds1" in charts
        assert "ds2" in charts

    async def test_chart_carries_dataset_metadata(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="revenue",
            description="Quarterly Revenue",
            categories=["Q1", "Q2"],
            series=[DataSeries(name="2025", values=[100, 200])],
            suggested_chart_type="bar",
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        chart = charts["revenue"]
        assert chart.title == "Quarterly Revenue"
        assert chart.categories == ["Q1", "Q2"]
        assert len(chart.series) == 1
        assert chart.series[0].name == "2025"

    async def test_chart_uses_profile_colors(self) -> None:
        engine = _make_engine()
        profile = _make_profile(color_palette=["#111111", "#222222"])
        ds = DataSet(
            name="test",
            categories=["A"],
            series=[DataSeries(name="S", values=[1])],
            suggested_chart_type="bar",
        )
        charts = await engine._resolve_chart_types([ds], profile)
        assert charts["test"].colors == ["#111111", "#222222"]

    async def test_chart_description_fallback_to_name(self) -> None:
        engine = _make_engine()
        ds = DataSet(
            name="my_data",
            description="",
            categories=["A"],
            series=[DataSeries(name="S", values=[1])],
            suggested_chart_type="bar",
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["my_data"].title == "my_data"


# ── Date/temporal detection helpers ──────────────────────────────────────


class TestDateDetection:
    """Tests for _looks_like_date and _categories_are_temporal."""

    def test_iso_date(self) -> None:
        assert _looks_like_date("2024-01-15") is True

    def test_iso_month(self) -> None:
        assert _looks_like_date("2024-01") is True

    def test_us_date(self) -> None:
        assert _looks_like_date("1/15/2024") is True

    def test_month_name(self) -> None:
        assert _looks_like_date("January") is True
        assert _looks_like_date("Jan") is True
        assert _looks_like_date("Feb 2024") is True

    def test_quarter(self) -> None:
        assert _looks_like_date("Q1") is True
        assert _looks_like_date("Q3 2024") is True

    def test_year_only(self) -> None:
        assert _looks_like_date("2024") is True

    def test_day_names(self) -> None:
        assert _looks_like_date("Monday") is True
        assert _looks_like_date("Wed") is True

    def test_week_number(self) -> None:
        assert _looks_like_date("Week 1") is True
        assert _looks_like_date("Week 52") is True

    def test_non_date_strings(self) -> None:
        assert _looks_like_date("Product A") is False
        assert _looks_like_date("East") is False
        assert _looks_like_date("") is False

    def test_temporal_categories(self) -> None:
        assert _categories_are_temporal(["Jan", "Feb", "Mar"]) is True
        assert _categories_are_temporal(["2020", "2021", "2022"]) is True
        assert _categories_are_temporal(["Q1", "Q2", "Q3", "Q4"]) is True

    def test_non_temporal_categories(self) -> None:
        assert _categories_are_temporal(["East", "West", "North"]) is False
        assert _categories_are_temporal(["Product A", "Product B"]) is False

    def test_empty_categories(self) -> None:
        assert _categories_are_temporal([]) is False

    def test_mixed_categories_majority_rule(self) -> None:
        # 2 out of 3 are temporal -> True (>= 50%)
        assert _categories_are_temporal(["Jan", "Feb", "Other"]) is True
        # 1 out of 3 are temporal -> False (< 50%)
        assert _categories_are_temporal(["Jan", "East", "West"]) is False


# ── Layout design ────────────────────────────────────────────────────────


class TestLayoutDesign:
    """Tests for _design_layout and prompt building."""

    async def test_layout_returns_design_spec(self) -> None:
        engine = _make_engine()
        brief = _make_brief()
        profile = _make_profile()
        spec = await engine._design_layout(brief, profile)

        assert isinstance(spec, DesignSpec)

    def test_layout_system_prompt_presentation(self) -> None:
        prompt = DesignEngine._build_layout_system_prompt(OutputType.PRESENTATION)
        assert "PRESENTATION" in prompt
        assert "slides" in prompt

    def test_layout_system_prompt_document(self) -> None:
        prompt = DesignEngine._build_layout_system_prompt(OutputType.DOCUMENT)
        assert "DOCUMENT" in prompt
        assert "document_sections" in prompt

    def test_layout_system_prompt_spreadsheet(self) -> None:
        prompt = DesignEngine._build_layout_system_prompt(OutputType.SPREADSHEET)
        assert "SPREADSHEET" in prompt
        assert "sheets" in prompt

    def test_layout_system_prompt_pdf(self) -> None:
        prompt = DesignEngine._build_layout_system_prompt(OutputType.PDF)
        assert "PDF" in prompt
        assert "document_sections" in prompt

    def test_layout_prompt_includes_title(self) -> None:
        brief = _make_brief(title="Annual Report")
        prompt = DesignEngine._build_layout_prompt(brief, _make_profile())
        assert "Annual Report" in prompt

    def test_layout_prompt_includes_section_count(self) -> None:
        sections = [
            ContentSection(heading="A"),
            ContentSection(heading="B"),
            ContentSection(heading="C"),
        ]
        brief = _make_brief(sections=sections)
        prompt = DesignEngine._build_layout_prompt(brief, _make_profile())
        assert "3" in prompt

    def test_layout_prompt_includes_section_details(self) -> None:
        brief = _make_brief(
            sections=[ContentSection(heading="Revenue", content="Revenue grew 15%")],
        )
        prompt = DesignEngine._build_layout_prompt(brief, _make_profile())
        assert "Revenue" in prompt

    def test_layout_prompt_includes_dataset_info(self) -> None:
        brief = _make_brief(
            datasets=[
                DataSet(name="sales", description="Monthly sales data"),
            ],
        )
        prompt = DesignEngine._build_layout_prompt(brief, _make_profile())
        assert "sales" in prompt
        assert "Monthly sales data" in prompt

    def test_layout_prompt_includes_profile_info(self) -> None:
        profile = _make_profile(heading_font="Helvetica", primary_color="#003366")
        brief = _make_brief()
        prompt = DesignEngine._build_layout_prompt(brief, profile)
        assert "Helvetica" in prompt
        assert "#003366" in prompt


# ── Constructor ──────────────────────────────────────────────────────────


class TestDesignEngineInit:
    """Tests for DesignEngine constructor."""

    def test_default_constructor(self) -> None:
        engine = DesignEngine()
        assert engine._model == ""
        assert engine._config is None

    def test_constructor_with_model(self) -> None:
        engine = DesignEngine(model=TestModel())
        assert engine._model is not None

    def test_constructor_with_tenant_config(self) -> None:
        engine = DesignEngine(model=TestModel(), tenant_config="some-config")
        assert engine._config == "some-config"

    def test_constructor_with_string_model(self) -> None:
        engine = DesignEngine(model="openai:gpt-4o")
        assert engine._model == "openai:gpt-4o"


# ── LLM-enhanced chart selection ──────────────────────────────────────


class TestLLMChartSelection:
    """Tests for LLM-enhanced chart type selection."""

    async def test_llm_chart_selection_called_for_default_bar(self) -> None:
        """When heuristic returns bar and LLM is enabled, LLM should be invoked."""
        engine = DesignEngine(model=TestModel(), use_llm_chart_selection=True)
        ds = DataSet(
            name="ambiguous",
            categories=["A", "B", "C", "D", "E", "F", "G", "H"],
            series=[DataSeries(name="Counts", values=[1, 2, 3, 4, 5, 6, 7, 8])],
        )
        # TestModel returns a string - LLM path is exercised
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert "ambiguous" in charts
        # TestModel returns a generic string, which won't be in valid set, so falls back to "bar"
        assert charts["ambiguous"].chart_type == "bar"

    async def test_llm_not_called_when_disabled(self) -> None:
        """When use_llm_chart_selection=False, only heuristic is used."""
        engine = DesignEngine(model=TestModel(), use_llm_chart_selection=False)
        ds = DataSet(
            name="test",
            categories=["A", "B", "C", "D", "E", "F", "G", "H"],
            series=[DataSeries(name="Counts", values=[1, 2, 3, 4, 5, 6, 7, 8])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["test"].chart_type == "bar"

    async def test_llm_not_called_when_suggested_type(self) -> None:
        """When suggested_chart_type is set, LLM should NOT be invoked."""
        engine = DesignEngine(model=TestModel(), use_llm_chart_selection=True)
        ds = DataSet(
            name="explicit",
            categories=["A", "B"],
            series=[DataSeries(name="S", values=[1, 2])],
            suggested_chart_type="doughnut",
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["explicit"].chart_type == "doughnut"

    async def test_llm_fallback_on_error(self) -> None:
        """When LLM call fails, heuristic result should stand."""
        engine = DesignEngine(model="invalid-model-that-fails", use_llm_chart_selection=True)
        ds = DataSet(
            name="fallback",
            categories=["A", "B", "C", "D", "E", "F", "G", "H"],
            series=[DataSeries(name="Counts", values=[1, 2, 3, 4, 5, 6, 7, 8])],
        )
        charts = await engine._resolve_chart_types([ds], _make_profile())
        assert charts["fallback"].chart_type == "bar"

    async def test_constructor_flag_default_false(self) -> None:
        engine = DesignEngine(model=TestModel())
        assert engine._use_llm_chart_selection is False

    async def test_constructor_flag_set_true(self) -> None:
        engine = DesignEngine(model=TestModel(), use_llm_chart_selection=True)
        assert engine._use_llm_chart_selection is True
