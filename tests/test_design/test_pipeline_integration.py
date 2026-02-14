"""Integration tests for the full design pipeline.

Tests the end-to-end flow: ContentBrief → DesignEngine → converter → SlideSpecs,
with autonomy checkpoints and backward compatibility checks.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from firefly_dworkers.design.converter import (
    convert_design_spec_to_slide_specs,
    convert_resolved_chart_to_chart_spec,
)
from firefly_dworkers.design.engine import DesignEngine
from firefly_dworkers.design.models import (
    ContentBrief,
    ContentSection,
    DataSeries,
    DataSet,
    DesignProfile,
    DesignSpec,
    ImageRequest,
    KeyMetric,
    OutputType,
    ResolvedChart,
    SlideDesign,
    StyledTable,
)
from firefly_dworkers.tools.presentation.models import SlideSpec
from firefly_dworkers.tools.presentation.pipeline import DesignPipelineTool
from firefly_dworkers.types import AutonomyLevel


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_brief(
    *,
    title: str = "Test Report",
    sections: list[ContentSection] | None = None,
    datasets: list[DataSet] | None = None,
) -> ContentBrief:
    """Build a ContentBrief for integration testing."""
    if sections is None:
        sections = [
            ContentSection(
                heading="Introduction",
                content="This is test content.",
                bullet_points=["Point one", "Point two"],
            ),
            ContentSection(
                heading="Data Analysis",
                content="Analysis of key metrics.",
                chart_ref="revenue",
            ),
        ]
    return ContentBrief(
        output_type=OutputType.PRESENTATION,
        title=title,
        sections=sections,
        audience="Test audience",
        tone="professional",
        purpose="Testing",
        datasets=datasets or [],
    )


def _make_spec_with_charts() -> DesignSpec:
    """Build a DesignSpec with charts for conversion testing."""
    return DesignSpec(
        profile=DesignProfile(
            primary_color="#1a3c6d",
            heading_font="Calibri",
            body_font="Arial",
            color_palette=["#1a3c6d", "#ff6600", "#333333"],
        ),
        output_type=OutputType.PRESENTATION,
        slides=[
            SlideDesign(
                layout="Title Slide",
                title="Q4 Report",
                subtitle="2024 Performance",
            ),
            SlideDesign(
                layout="Title and Content",
                title="Revenue Analysis",
                chart_ref="revenue",
            ),
            SlideDesign(
                layout="Title and Content",
                title="Summary",
                table=StyledTable(
                    headers=["Metric", "Value"],
                    rows=[["Revenue", "$10M"], ["Profit", "$2M"]],
                ),
            ),
        ],
        charts={
            "revenue": ResolvedChart(
                chart_type="bar",
                title="Revenue by Quarter",
                categories=["Q1", "Q2", "Q3", "Q4"],
                series=[
                    DataSeries(name="2023", values=[100, 200, 300, 400]),
                    DataSeries(name="2024", values=[150, 250, 350, 450]),
                ],
                colors=["#1a3c6d", "#ff6600"],
            ),
        },
    )


class _ApproveAllHandler:
    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return True


class _RejectHandler:
    def __init__(self, reject_at: str) -> None:
        self._reject_at = reject_at

    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return phase != self._reject_at


# ── DesignEngine → DesignSpec integration ──────────────────────────────────


class TestEngineIntegration:
    """Test DesignEngine produces valid DesignSpec from ContentBrief."""

    async def test_engine_produces_design_spec(self) -> None:
        """DesignEngine.design() returns a DesignSpec with correct output_type."""
        engine = DesignEngine(TestModel())
        brief = _make_brief()

        spec = await engine.design(brief)

        assert isinstance(spec, DesignSpec)
        assert spec.output_type == OutputType.PRESENTATION
        assert spec.profile is not None

    async def test_engine_with_datasets(self) -> None:
        """DesignEngine resolves chart types for datasets."""
        engine = DesignEngine(TestModel())
        brief = _make_brief(
            datasets=[
                DataSet(
                    name="revenue",
                    description="Quarterly Revenue",
                    categories=["Q1", "Q2", "Q3", "Q4"],
                    series=[DataSeries(name="Sales", values=[100, 200, 300, 400])],
                ),
            ]
        )

        spec = await engine.design(brief)

        assert "revenue" in spec.charts
        assert spec.charts["revenue"].chart_type in {"bar", "line", "pie", "scatter", "area"}

    async def test_engine_with_profile(self) -> None:
        """DesignEngine uses provided profile without generating one."""
        engine = DesignEngine(TestModel())
        brief = _make_brief()
        profile = DesignProfile(
            primary_color="#ff0000",
            heading_font="Georgia",
        )

        spec = await engine.design(brief, profile)

        assert spec.profile is profile
        assert spec.profile.primary_color == "#ff0000"


# ── DesignSpec → SlideSpec conversion integration ──────────────────────────


class TestConversionIntegration:
    """Test full DesignSpec → SlideSpec conversion pipeline."""

    def test_full_spec_conversion(self) -> None:
        """Convert a complete DesignSpec with charts and tables."""
        spec = _make_spec_with_charts()

        slide_specs = convert_design_spec_to_slide_specs(spec)

        assert len(slide_specs) == 3

        # Title slide
        assert slide_specs[0].title == "Q4 Report"
        assert slide_specs[0].layout == "Title Slide"

        # Chart slide
        assert slide_specs[1].title == "Revenue Analysis"
        assert slide_specs[1].chart is not None
        assert slide_specs[1].chart.chart_type == "bar"
        assert len(slide_specs[1].chart.categories) == 4
        assert len(slide_specs[1].chart.series) == 2

        # Table slide
        assert slide_specs[2].title == "Summary"
        assert slide_specs[2].table is not None
        assert slide_specs[2].table.headers == ["Metric", "Value"]
        assert len(slide_specs[2].table.rows) == 2

    def test_charts_preserve_data(self) -> None:
        """Chart conversion preserves all data series and categories."""
        chart = ResolvedChart(
            chart_type="line",
            title="Trend",
            categories=["Jan", "Feb", "Mar"],
            series=[
                DataSeries(name="2023", values=[10.5, 20.3, 30.1]),
                DataSeries(name="2024", values=[15.0, 25.0, 35.0]),
            ],
            colors=["#ff0000", "#00ff00"],
            show_legend=True,
            show_data_labels=True,
            stacked=True,
        )

        chart_spec = convert_resolved_chart_to_chart_spec(chart)

        assert chart_spec.chart_type == "line"
        assert chart_spec.categories == ["Jan", "Feb", "Mar"]
        assert len(chart_spec.series) == 2
        assert chart_spec.series[0]["name"] == "2023"
        assert chart_spec.series[0]["values"] == [10.5, 20.3, 30.1]
        assert chart_spec.colors == ["#ff0000", "#00ff00"]
        assert chart_spec.show_legend is True
        assert chart_spec.show_data_labels is True
        assert chart_spec.stacked is True


# ── Autonomy checkpoint integration ───────────────────────────────────────


class TestAutonomyCheckpointIntegration:
    """Test that autonomy checkpoints gate the pipeline correctly."""

    async def test_semi_supervised_checkpoints_design_spec(self) -> None:
        """SEMI_SUPERVISED gates at design_spec_approval."""
        from firefly_dworkers.autonomy.levels import should_checkpoint

        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "design_spec_approval") is True
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "pre_render") is True
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "deliverable") is True
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "internal_step") is False

    async def test_pipeline_approved_produces_result(self) -> None:
        """Pipeline with approving handler succeeds."""
        spec = _make_spec_with_charts()

        engine_cls = MagicMock()
        engine_inst = AsyncMock()
        engine_inst.design = AsyncMock(return_value=spec)
        engine_cls.return_value = engine_inst

        pptx_tool = AsyncMock()
        pptx_tool.create = AsyncMock(return_value=b"PK\x03\x04fake")

        registry = MagicMock()
        registry.has.return_value = True
        registry.create.return_value = pptx_tool

        convert = MagicMock(return_value=[SlideSpec(title="s1")])

        handler = _ApproveAllHandler()
        pipeline = DesignPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        with (
            patch("firefly_dworkers.design.engine.DesignEngine", engine_cls),
            patch("firefly_dworkers.tools.presentation.pipeline.tool_registry", registry),
            patch("firefly_dworkers.design.converter.convert_design_spec_to_slide_specs", convert),
        ):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is True

    async def test_pipeline_rejected_at_design_spec(self) -> None:
        """Pipeline with rejecting handler at design_spec_approval fails."""
        spec = _make_spec_with_charts()

        engine_cls = MagicMock()
        engine_inst = AsyncMock()
        engine_inst.design = AsyncMock(return_value=spec)
        engine_cls.return_value = engine_inst

        handler = _RejectHandler("design_spec_approval")
        pipeline = DesignPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        convert = MagicMock(return_value=[SlideSpec(title="s1")])

        with (
            patch("firefly_dworkers.design.engine.DesignEngine", engine_cls),
            patch("firefly_dworkers.design.converter.convert_design_spec_to_slide_specs", convert),
        ):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is False
        assert "rejected" in result["reason"].lower()


# ── Backward compatibility ────────────────────────────────────────────────


class TestBackwardCompatibility:
    """Ensure direct SlideSpec usage still works alongside the new pipeline."""

    def test_slide_spec_direct_construction(self) -> None:
        """SlideSpec can be constructed directly without the pipeline."""
        spec = SlideSpec(
            layout="Title and Content",
            title="Direct Slide",
            content="This is direct content.",
            bullet_points=["Bullet 1", "Bullet 2"],
        )
        assert spec.title == "Direct Slide"
        assert len(spec.bullet_points) == 2

    def test_slide_spec_with_chart(self) -> None:
        """SlideSpec with ChartSpec works as before."""
        from firefly_dworkers.tools.presentation.models import ChartSpec

        chart = ChartSpec(
            chart_type="bar",
            title="Test Chart",
            categories=["A", "B"],
            series=[{"name": "S1", "values": [10, 20]}],
        )
        spec = SlideSpec(title="Chart Slide", chart=chart)
        assert spec.chart is not None
        assert spec.chart.chart_type == "bar"

    def test_designer_toolkit_still_works(self) -> None:
        """designer_toolkit() still produces a valid toolkit."""
        from fireflyframework_genai.tools.toolkit import ToolKit

        from firefly_dworkers.tenants.config import TenantConfig
        from firefly_dworkers.tools.toolkits import designer_toolkit

        config = TenantConfig(id="test", name="Test")
        kit = designer_toolkit(config)
        assert isinstance(kit, ToolKit)
        tool_names = [t.name for t in kit.tools]
        assert "report_generation" in tool_names
        assert "design_pipeline" in tool_names

    def test_design_pipeline_tool_registered(self) -> None:
        """DesignPipelineTool is registered in the tool registry."""
        from firefly_dworkers.tools.registry import tool_registry

        assert tool_registry.has("design_pipeline")
        cls = tool_registry.get_class("design_pipeline")
        assert cls is DesignPipelineTool
