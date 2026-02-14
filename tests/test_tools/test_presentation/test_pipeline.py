"""Tests for DesignPipelineTool -- full pipeline from content brief to PPTX."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from firefly_dworkers.design.models import (
    ContentBrief,
    ContentSection,
    DataSeries,
    DataSet,
    DesignProfile,
    DesignSpec,
    ImageRequest,
    OutputType,
    ResolvedImage,
    SlideDesign,
)
from firefly_dworkers.tools.presentation.models import SlideSpec
from firefly_dworkers.tools.presentation.pipeline import DesignPipelineTool
from firefly_dworkers.types import AutonomyLevel

# Patch targets for lazy imports inside _execute()
_ENGINE = "firefly_dworkers.design.engine.DesignEngine"
_ANALYZER = "firefly_dworkers.design.analyzer.TemplateAnalyzer"
_CONVERTER = "firefly_dworkers.design.converter.convert_design_spec_to_slide_specs"
_VALIDATOR = "firefly_dworkers.design.validator.SlideValidator"
# tool_registry is imported at module level in pipeline.py
_REGISTRY = "firefly_dworkers.tools.presentation.pipeline.tool_registry"


# ── Helpers ─────────────────────────────────────────────────────────────────


class _RejectingCheckpointHandler:
    """Checkpoint handler that rejects a specific checkpoint type."""

    def __init__(self, reject_type: str) -> None:
        self._reject_type = reject_type

    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return phase != self._reject_type


class _ApprovingCheckpointHandler:
    """Checkpoint handler that approves everything."""

    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return True


def _make_design_spec() -> DesignSpec:
    """Create a minimal DesignSpec for mocking."""
    return DesignSpec(
        profile=DesignProfile(primary_color="#1a3c6d"),
        output_type=OutputType.PRESENTATION,
        slides=[
            SlideDesign(layout="Title Slide", title="Test Title"),
            SlideDesign(layout="Title and Content", title="Slide 2"),
        ],
    )


def _mock_pipeline_deps(
    spec: DesignSpec | None = None,
    pptx_bytes: bytes = b"PK\x03\x04fake",
    slide_specs: list[SlideSpec] | None = None,
):
    """Create standard mocks for engine, registry, and converter."""
    if spec is None:
        spec = _make_design_spec()
    if slide_specs is None:
        slide_specs = [SlideSpec(title=f"s{i}") for i in range(len(spec.slides))]

    mock_engine_instance = AsyncMock()
    mock_engine_instance.design = AsyncMock(return_value=spec)
    mock_engine_cls = MagicMock(return_value=mock_engine_instance)

    mock_pptx_tool = AsyncMock()
    mock_pptx_tool.create = AsyncMock(return_value=pptx_bytes)

    mock_registry = MagicMock()
    mock_registry.has.return_value = True
    mock_registry.create.return_value = mock_pptx_tool

    mock_convert = MagicMock(return_value=slide_specs)

    return mock_engine_cls, mock_engine_instance, mock_registry, mock_pptx_tool, mock_convert, slide_specs


# ── Build brief from kwargs ────────────────────────────────────────────────


class TestBuildBrief:
    """Tests for _build_brief static method."""

    def test_basic_brief(self) -> None:
        kwargs = {
            "title": "Q4 Report",
            "sections": [{"heading": "Overview", "content": "Sales grew 15%"}],
        }
        brief = DesignPipelineTool._build_brief(kwargs)

        assert isinstance(brief, ContentBrief)
        assert brief.title == "Q4 Report"
        assert brief.output_type == OutputType.PRESENTATION
        assert len(brief.sections) == 1
        assert brief.sections[0].heading == "Overview"

    def test_brief_with_datasets(self) -> None:
        kwargs = {
            "title": "Sales",
            "sections": [],
            "datasets": [
                {
                    "name": "revenue",
                    "description": "Monthly revenue",
                    "categories": ["Jan", "Feb", "Mar"],
                    "series": [{"name": "2024", "values": [100, 200, 300]}],
                }
            ],
        }
        brief = DesignPipelineTool._build_brief(kwargs)

        assert len(brief.datasets) == 1
        assert brief.datasets[0].name == "revenue"
        assert len(brief.datasets[0].series) == 1
        assert brief.datasets[0].series[0].name == "2024"

    def test_brief_with_image_requests(self) -> None:
        kwargs = {
            "title": "Report",
            "sections": [],
            "image_requests": [
                {"name": "logo", "source_type": "file", "file_path": "/tmp/logo.png"}
            ],
        }
        brief = DesignPipelineTool._build_brief(kwargs)

        assert len(brief.image_requests) == 1
        assert brief.image_requests[0].name == "logo"
        assert brief.image_requests[0].source_type == "file"

    def test_brief_with_model_objects(self) -> None:
        """ContentSection and DataSet model objects pass through directly."""
        section = ContentSection(heading="Intro", content="Hello")
        dataset = DataSet(name="ds1", series=[DataSeries(name="s1", values=[1, 2])])
        img = ImageRequest(name="img1", source_type="url", url="https://example.com/img.png")

        kwargs = {
            "title": "Test",
            "sections": [section],
            "datasets": [dataset],
            "image_requests": [img],
        }
        brief = DesignPipelineTool._build_brief(kwargs)

        assert brief.sections[0] is section
        assert brief.datasets[0] is dataset
        assert brief.image_requests[0] is img

    def test_brief_with_optional_fields(self) -> None:
        kwargs = {
            "title": "Report",
            "sections": [],
            "audience": "Executives",
            "tone": "professional",
            "purpose": "Quarterly review",
            "brand_colors": ["#1a3c6d", "#ff6600"],
            "brand_fonts": ["Calibri"],
        }
        brief = DesignPipelineTool._build_brief(kwargs)

        assert brief.audience == "Executives"
        assert brief.tone == "professional"
        assert brief.purpose == "Quarterly review"
        assert brief.brand_colors == ["#1a3c6d", "#ff6600"]
        assert brief.brand_fonts == ["Calibri"]


# ── Pipeline execution ──────────────────────────────────────────────────────


class TestPipelineExecution:
    """Tests for the full pipeline _execute method."""

    async def test_pipeline_produces_result(self) -> None:
        """Full pipeline with mocked engine and PowerPoint tool."""
        fake_pptx = b"PK\x03\x04fake-pptx-bytes"
        engine_cls, _, registry, pptx_tool, convert, slide_specs = _mock_pipeline_deps(
            pptx_bytes=fake_pptx,
        )

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DesignPipelineTool(model="test")
            result = await pipeline._execute(
                title="Test Report",
                sections=[{"heading": "Intro", "content": "Hello world"}],
            )

        assert result["success"] is True
        assert result["slide_count"] == len(slide_specs)
        assert result["bytes_length"] == len(fake_pptx)
        assert pipeline.artifact_bytes == fake_pptx

    async def test_pipeline_with_template(self) -> None:
        """Pipeline with template_path triggers TemplateAnalyzer."""
        mock_profile = DesignProfile(primary_color="#123456")
        engine_cls, engine_inst, registry, _, convert, _ = _mock_pipeline_deps()

        mock_analyzer_inst = AsyncMock()
        mock_analyzer_inst.analyze = AsyncMock(return_value=mock_profile)
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer_inst)

        with (
            patch(_ENGINE, engine_cls),
            patch(_ANALYZER, mock_analyzer_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DesignPipelineTool(model="test")
            result = await pipeline._execute(
                title="Test",
                sections=[],
                template_path="/tmp/template.pptx",
            )

        assert result["success"] is True
        mock_analyzer_inst.analyze.assert_awaited_once_with("/tmp/template.pptx")
        # Profile should have been passed to design()
        engine_inst.design.assert_awaited_once()
        call_args = engine_inst.design.call_args
        assert call_args[0][1] is mock_profile


# ── Checkpoint tests ────────────────────────────────────────────────────────


class TestPipelineCheckpoints:
    """Tests for autonomy checkpoint integration."""

    async def test_checkpoint_rejection_stops_at_design_spec(self) -> None:
        """Rejecting design_spec_approval stops the pipeline."""
        engine_cls, _, _, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("design_spec_approval")
        pipeline = DesignPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        with patch(_ENGINE, engine_cls), patch(_CONVERTER, convert):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is False
        assert "rejected" in result["reason"].lower()

    async def test_checkpoint_rejection_stops_at_pre_render(self) -> None:
        """Rejecting pre_render stops the pipeline."""
        engine_cls, _, _, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("pre_render")
        pipeline = DesignPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        with patch(_ENGINE, engine_cls), patch(_CONVERTER, convert):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is False
        assert "rejected" in result["reason"].lower()

    async def test_autonomous_skips_checkpoints(self) -> None:
        """AUTONOMOUS level skips all checkpoints."""
        engine_cls, _, registry, _, convert, _ = _mock_pipeline_deps()

        # Handler that would reject everything — but should never be called
        handler = _RejectingCheckpointHandler("design_spec_approval")
        pipeline = DesignPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.AUTONOMOUS,
            checkpoint_handler=handler,
        )

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is True

    async def test_no_handler_auto_approves(self) -> None:
        """No checkpoint handler means auto-approve."""
        engine_cls, _, registry, _, convert, _ = _mock_pipeline_deps()

        pipeline = DesignPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.MANUAL,
            # No checkpoint_handler set
        )

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is True


# ── Tool registration ──────────────────────────────────────────────────────


class TestPipelineRegistration:
    """Tests for tool registry integration."""

    def test_tool_registered(self) -> None:
        """DesignPipelineTool should be registered as 'design_pipeline'."""
        from firefly_dworkers.tools.registry import tool_registry

        assert tool_registry.has("design_pipeline")
        assert tool_registry.get_category("design_pipeline") == "presentation"

    def test_tool_class_correct(self) -> None:
        """Registered class should be DesignPipelineTool."""
        from firefly_dworkers.tools.registry import tool_registry

        cls = tool_registry.get_class("design_pipeline")
        assert cls is DesignPipelineTool


# ── VLM validation ──────────────────────────────────────────────────────────


class TestPipelineValidation:
    """Tests for optional VLM validation."""

    async def test_validation_included_when_enabled(self) -> None:
        """When enable_validation=True and vlm_model set, validation runs."""
        fake_pptx = b"PK\x03\x04fake"
        engine_cls, _, registry, _, convert, _ = _mock_pipeline_deps(pptx_bytes=fake_pptx)

        mock_validation = MagicMock()
        mock_validation.overall_score = 8.5
        mock_validation.summary = "Good quality"

        mock_validator_inst = AsyncMock()
        mock_validator_inst.validate = AsyncMock(return_value=mock_validation)
        mock_validator_cls = MagicMock(return_value=mock_validator_inst)

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
            patch(_VALIDATOR, mock_validator_cls),
        ):
            pipeline = DesignPipelineTool(
                model="test",
                vlm_model="test-vlm",
                enable_validation=True,
            )
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is True
        assert result["validation_score"] == 8.5
        assert result["validation_summary"] == "Good quality"

    async def test_validation_not_run_when_disabled(self) -> None:
        """When enable_validation=False, no validation runs."""
        engine_cls, _, registry, _, convert, _ = _mock_pipeline_deps()

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DesignPipelineTool(model="test")
            result = await pipeline._execute(title="Test", sections=[])

        assert "validation_score" not in result
