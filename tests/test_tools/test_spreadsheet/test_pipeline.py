"""Tests for SpreadsheetPipelineTool -- full pipeline from content brief to XLSX."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from firefly_dworkers.design.models import (
    ContentBrief,
    DesignProfile,
    DesignSpec,
    OutputType,
    SheetDesign,
)
from firefly_dworkers.tools.spreadsheet.models import SheetSpec
from firefly_dworkers.tools.spreadsheet.pipeline import SpreadsheetPipelineTool
from firefly_dworkers.types import AutonomyLevel

# Patch targets for lazy imports inside _execute()
_ENGINE = "firefly_dworkers.design.engine.DesignEngine"
_ANALYZER = "firefly_dworkers.design.analyzer.TemplateAnalyzer"
_CONVERTER = "firefly_dworkers.design.converter.convert_design_spec_to_sheet_specs"
_REGISTRY = "firefly_dworkers.tools.spreadsheet.pipeline.tool_registry"


# ── Helpers ─────────────────────────────────────────────────────────────────


class _RejectingCheckpointHandler:
    def __init__(self, reject_type: str) -> None:
        self._reject_type = reject_type

    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return phase != self._reject_type


def _make_design_spec() -> DesignSpec:
    return DesignSpec(
        profile=DesignProfile(primary_color="#1a3c6d"),
        output_type=OutputType.SPREADSHEET,
        sheets=[
            SheetDesign(name="Revenue"),
            SheetDesign(name="Expenses"),
        ],
    )


def _mock_pipeline_deps(
    spec: DesignSpec | None = None,
    xlsx_bytes: bytes = b"PK\x03\x04fake-xlsx",
    sheet_specs: list[SheetSpec] | None = None,
):
    if spec is None:
        spec = _make_design_spec()
    if sheet_specs is None:
        sheet_specs = [SheetSpec(name=f"s{i}") for i in range(len(spec.sheets))]

    mock_engine_instance = AsyncMock()
    mock_engine_instance.design = AsyncMock(return_value=spec)
    mock_engine_cls = MagicMock(return_value=mock_engine_instance)

    mock_excel_tool = AsyncMock()
    mock_excel_tool.create = AsyncMock(return_value=xlsx_bytes)

    mock_registry = MagicMock()
    mock_registry.has.return_value = True
    mock_registry.create.return_value = mock_excel_tool

    mock_convert = MagicMock(return_value=sheet_specs)

    return mock_engine_cls, mock_engine_instance, mock_registry, mock_excel_tool, mock_convert, sheet_specs


# ── Build brief from kwargs ────────────────────────────────────────────────


class TestBuildBrief:
    def test_basic_brief(self) -> None:
        kwargs = {
            "title": "Financial Report",
            "sections": [{"heading": "Revenue", "content": "Q4 revenue grew."}],
        }
        brief = SpreadsheetPipelineTool._build_brief(kwargs)
        assert isinstance(brief, ContentBrief)
        assert brief.title == "Financial Report"
        assert brief.output_type == OutputType.SPREADSHEET
        assert len(brief.sections) == 1

    def test_brief_with_datasets(self) -> None:
        kwargs = {
            "title": "Data",
            "sections": [],
            "datasets": [
                {
                    "name": "revenue",
                    "categories": ["Q1", "Q2"],
                    "series": [{"name": "2025", "values": [100, 200]}],
                }
            ],
        }
        brief = SpreadsheetPipelineTool._build_brief(kwargs)
        assert len(brief.datasets) == 1
        assert brief.datasets[0].name == "revenue"


# ── Pipeline execution ──────────────────────────────────────────────────────


class TestPipelineExecution:
    async def test_pipeline_produces_result(self) -> None:
        fake_xlsx = b"PK\x03\x04fake-xlsx-bytes"
        engine_cls, _, registry, excel_tool, convert, sheet_specs = _mock_pipeline_deps(
            xlsx_bytes=fake_xlsx,
        )

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = SpreadsheetPipelineTool(model="test")
            result = await pipeline._execute(
                title="Test Workbook",
                sections=[{"heading": "Data", "content": "Revenue data"}],
            )

        assert result["success"] is True
        assert result["sheet_count"] == len(sheet_specs)
        assert result["bytes_length"] == len(fake_xlsx)
        assert pipeline.artifact_bytes == fake_xlsx
        excel_tool.create.assert_awaited_once()

    async def test_pipeline_calls_engine(self) -> None:
        engine_cls, engine_inst, registry, _, convert, _ = _mock_pipeline_deps()

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = SpreadsheetPipelineTool(model="test")
            await pipeline._execute(title="Test", sections=[])

        engine_inst.design.assert_awaited_once()

    async def test_pipeline_converts_specs(self) -> None:
        engine_cls, _, registry, _, convert, _ = _mock_pipeline_deps()

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = SpreadsheetPipelineTool(model="test")
            await pipeline._execute(title="Test", sections=[])

        convert.assert_called_once()

    async def test_pipeline_renders_xlsx(self) -> None:
        engine_cls, _, registry, excel_tool, convert, _ = _mock_pipeline_deps()

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = SpreadsheetPipelineTool(model="test")
            await pipeline._execute(title="Test", sections=[])

        excel_tool.create.assert_awaited_once()


# ── Checkpoint tests ────────────────────────────────────────────────────────


class TestPipelineCheckpoints:
    async def test_checkpoint_rejection_stops_at_design_spec(self) -> None:
        engine_cls, _, _, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("design_spec_approval")
        pipeline = SpreadsheetPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        with patch(_ENGINE, engine_cls), patch(_CONVERTER, convert):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is False
        assert "rejected" in result["reason"].lower()

    async def test_checkpoint_rejection_stops_at_pre_render(self) -> None:
        engine_cls, _, _, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("pre_render")
        pipeline = SpreadsheetPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        with patch(_ENGINE, engine_cls), patch(_CONVERTER, convert):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is False
        assert "rejected" in result["reason"].lower()

    async def test_autonomous_skips_checkpoints(self) -> None:
        engine_cls, _, registry, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("design_spec_approval")
        pipeline = SpreadsheetPipelineTool(
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


# ── Tool registration ──────────────────────────────────────────────────────


class TestPipelineRegistration:
    def test_tool_registered(self) -> None:
        from firefly_dworkers.tools.registry import tool_registry

        assert tool_registry.has("spreadsheet_design_pipeline")
        assert tool_registry.get_category("spreadsheet_design_pipeline") == "spreadsheet"

    def test_tool_class_correct(self) -> None:
        from firefly_dworkers.tools.registry import tool_registry

        cls = tool_registry.get_class("spreadsheet_design_pipeline")
        assert cls is SpreadsheetPipelineTool
