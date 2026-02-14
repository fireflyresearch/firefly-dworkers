"""Tests for DocumentPipelineTool -- full pipeline from content brief to DOCX/PDF."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from firefly_dworkers.design.models import (
    ContentBrief,
    DesignProfile,
    DesignSpec,
    OutputType,
    SectionDesign,
)
from firefly_dworkers.tools.document.models import SectionSpec
from firefly_dworkers.tools.document.pipeline import DocumentPipelineTool
from firefly_dworkers.types import AutonomyLevel

# Patch targets for lazy imports inside _execute()
_ENGINE = "firefly_dworkers.design.engine.DesignEngine"
_ANALYZER = "firefly_dworkers.design.analyzer.TemplateAnalyzer"
_CONVERTER = "firefly_dworkers.design.converter.convert_design_spec_to_section_specs"
_REGISTRY = "firefly_dworkers.tools.document.pipeline.tool_registry"


# ── Helpers ─────────────────────────────────────────────────────────────────


class _RejectingCheckpointHandler:
    def __init__(self, reject_type: str) -> None:
        self._reject_type = reject_type

    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return phase != self._reject_type


class _ApprovingCheckpointHandler:
    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return True


def _make_design_spec() -> DesignSpec:
    return DesignSpec(
        profile=DesignProfile(primary_color="#1a3c6d"),
        output_type=OutputType.DOCUMENT,
        document_sections=[
            SectionDesign(heading="Introduction"),
            SectionDesign(heading="Findings"),
        ],
    )


def _mock_pipeline_deps(
    spec: DesignSpec | None = None,
    doc_bytes: bytes = b"PK\x03\x04fake-docx",
    section_specs: list[SectionSpec] | None = None,
):
    if spec is None:
        spec = _make_design_spec()
    if section_specs is None:
        section_specs = [SectionSpec(heading=f"s{i}") for i in range(len(spec.document_sections))]

    mock_engine_instance = AsyncMock()
    mock_engine_instance.design = AsyncMock(return_value=spec)
    mock_engine_cls = MagicMock(return_value=mock_engine_instance)

    mock_word_tool = AsyncMock()
    mock_word_tool.create = AsyncMock(return_value=doc_bytes)

    mock_pdf_tool = AsyncMock()
    mock_pdf_tool.generate = AsyncMock(return_value=b"%PDF-fake")

    def _create_tool(name, **kw):
        if name == "word":
            return mock_word_tool
        if name == "pdf":
            return mock_pdf_tool
        raise KeyError(name)

    mock_registry = MagicMock()
    mock_registry.has.return_value = True
    mock_registry.create.side_effect = _create_tool

    mock_convert = MagicMock(return_value=section_specs)

    return mock_engine_cls, mock_engine_instance, mock_registry, mock_word_tool, mock_pdf_tool, mock_convert, section_specs


# ── Build brief from kwargs ────────────────────────────────────────────────


class TestBuildBrief:
    def test_basic_brief(self) -> None:
        kwargs = {
            "title": "Annual Report",
            "sections": [{"heading": "Overview", "content": "Growth was strong."}],
        }
        brief = DocumentPipelineTool._build_brief(kwargs)
        assert isinstance(brief, ContentBrief)
        assert brief.title == "Annual Report"
        assert brief.output_type == OutputType.DOCUMENT
        assert len(brief.sections) == 1
        assert brief.sections[0].heading == "Overview"

    def test_brief_pdf_output_type(self) -> None:
        kwargs = {"title": "Report", "sections": []}
        brief = DocumentPipelineTool._build_brief(kwargs, output_format="pdf")
        assert brief.output_type == OutputType.PDF

    def test_brief_with_optional_fields(self) -> None:
        kwargs = {
            "title": "Report",
            "sections": [],
            "audience": "Board",
            "tone": "formal",
            "purpose": "Annual review",
        }
        brief = DocumentPipelineTool._build_brief(kwargs)
        assert brief.audience == "Board"
        assert brief.tone == "formal"
        assert brief.purpose == "Annual review"


# ── Pipeline execution ──────────────────────────────────────────────────────


class TestPipelineExecution:
    async def test_pipeline_produces_docx_result(self) -> None:
        fake_docx = b"PK\x03\x04fake-docx-bytes"
        engine_cls, _, registry, word_tool, _, convert, section_specs = _mock_pipeline_deps(
            doc_bytes=fake_docx,
        )

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DocumentPipelineTool(model="test")
            result = await pipeline._execute(
                title="Test Report",
                sections=[{"heading": "Intro", "content": "Hello"}],
            )

        assert result["success"] is True
        assert result["section_count"] == len(section_specs)
        assert result["bytes_length"] == len(fake_docx)
        assert result["output_format"] == "docx"
        assert pipeline.artifact_bytes == fake_docx
        word_tool.create.assert_awaited_once()

    async def test_pipeline_produces_pdf_result(self) -> None:
        engine_cls, _, registry, _, pdf_tool, convert, section_specs = _mock_pipeline_deps()

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DocumentPipelineTool(model="test")
            result = await pipeline._execute(
                title="Test Report",
                sections=[{"heading": "Intro"}],
                output_format="pdf",
            )

        assert result["success"] is True
        assert result["output_format"] == "pdf"
        pdf_tool.generate.assert_awaited_once()

    async def test_pipeline_calls_engine(self) -> None:
        engine_cls, engine_inst, registry, _, _, convert, _ = _mock_pipeline_deps()

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DocumentPipelineTool(model="test")
            await pipeline._execute(title="Test", sections=[])

        engine_inst.design.assert_awaited_once()

    async def test_pipeline_converts_specs(self) -> None:
        engine_cls, _, registry, _, _, convert, _ = _mock_pipeline_deps()

        with (
            patch(_ENGINE, engine_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DocumentPipelineTool(model="test")
            await pipeline._execute(title="Test", sections=[])

        convert.assert_called_once()

    async def test_pipeline_with_template(self) -> None:
        mock_profile = DesignProfile(primary_color="#123456")
        engine_cls, engine_inst, registry, _, _, convert, _ = _mock_pipeline_deps()

        mock_analyzer_inst = AsyncMock()
        mock_analyzer_inst.analyze = AsyncMock(return_value=mock_profile)
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer_inst)

        with (
            patch(_ENGINE, engine_cls),
            patch(_ANALYZER, mock_analyzer_cls),
            patch(_REGISTRY, registry),
            patch(_CONVERTER, convert),
        ):
            pipeline = DocumentPipelineTool(model="test")
            result = await pipeline._execute(
                title="Test",
                sections=[],
                template_path="/tmp/template.docx",
            )

        assert result["success"] is True
        mock_analyzer_inst.analyze.assert_awaited_once_with("/tmp/template.docx")


# ── Checkpoint tests ────────────────────────────────────────────────────────


class TestPipelineCheckpoints:
    async def test_checkpoint_rejection_stops_at_design_spec(self) -> None:
        engine_cls, _, _, _, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("design_spec_approval")
        pipeline = DocumentPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        with patch(_ENGINE, engine_cls), patch(_CONVERTER, convert):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is False
        assert "rejected" in result["reason"].lower()

    async def test_checkpoint_rejection_stops_at_pre_render(self) -> None:
        engine_cls, _, _, _, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("pre_render")
        pipeline = DocumentPipelineTool(
            model="test",
            autonomy_level=AutonomyLevel.SEMI_SUPERVISED,
            checkpoint_handler=handler,
        )

        with patch(_ENGINE, engine_cls), patch(_CONVERTER, convert):
            result = await pipeline._execute(title="Test", sections=[])

        assert result["success"] is False
        assert "rejected" in result["reason"].lower()

    async def test_autonomous_skips_checkpoints(self) -> None:
        engine_cls, _, registry, _, _, convert, _ = _mock_pipeline_deps()

        handler = _RejectingCheckpointHandler("design_spec_approval")
        pipeline = DocumentPipelineTool(
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

        assert tool_registry.has("document_design_pipeline")
        assert tool_registry.get_category("document_design_pipeline") == "document"

    def test_tool_class_correct(self) -> None:
        from firefly_dworkers.tools.registry import tool_registry

        cls = tool_registry.get_class("document_design_pipeline")
        assert cls is DocumentPipelineTool
