"""Tests for UnifiedDesignPipeline -- dispatcher to format-specific pipelines."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from firefly_dworkers.tools.design_pipeline import UnifiedDesignPipeline

_REGISTRY = "firefly_dworkers.tools.design_pipeline.tool_registry"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _mock_sub_pipeline(result: dict[str, Any] | None = None):
    """Create a mock pipeline tool that returns the given result."""
    if result is None:
        result = {"success": True}
    mock = AsyncMock()
    mock._execute = AsyncMock(return_value=result)
    return mock


# ── Dispatch tests ──────────────────────────────────────────────────────────


class TestDispatch:
    async def test_dispatches_presentation(self) -> None:
        mock_pipeline = _mock_sub_pipeline({"success": True, "slide_count": 5})

        mock_registry = MagicMock()
        mock_registry.has.return_value = True
        mock_registry.create.return_value = mock_pipeline

        with patch(_REGISTRY, mock_registry):
            unified = UnifiedDesignPipeline(model="test")
            result = await unified._execute(
                output_type="presentation",
                title="Test",
                sections=[],
            )

        assert result["success"] is True
        mock_registry.create.assert_called_once_with(
            "design_pipeline",
            model="test",
            vlm_model="",
            autonomy_level="autonomous",
            checkpoint_handler=None,
        )

    async def test_dispatches_document(self) -> None:
        mock_pipeline = _mock_sub_pipeline({"success": True, "section_count": 3})

        mock_registry = MagicMock()
        mock_registry.has.return_value = True
        mock_registry.create.return_value = mock_pipeline

        with patch(_REGISTRY, mock_registry):
            unified = UnifiedDesignPipeline(model="test")
            result = await unified._execute(
                output_type="document",
                title="Report",
                sections=[],
            )

        assert result["success"] is True
        mock_registry.create.assert_called_once_with(
            "document_design_pipeline",
            model="test",
            vlm_model="",
            autonomy_level="autonomous",
            checkpoint_handler=None,
        )

    async def test_dispatches_spreadsheet(self) -> None:
        mock_pipeline = _mock_sub_pipeline({"success": True, "sheet_count": 2})

        mock_registry = MagicMock()
        mock_registry.has.return_value = True
        mock_registry.create.return_value = mock_pipeline

        with patch(_REGISTRY, mock_registry):
            unified = UnifiedDesignPipeline(model="test")
            result = await unified._execute(
                output_type="spreadsheet",
                title="Data",
                sections=[],
            )

        assert result["success"] is True
        mock_registry.create.assert_called_once_with(
            "spreadsheet_design_pipeline",
            model="test",
            vlm_model="",
            autonomy_level="autonomous",
            checkpoint_handler=None,
        )

    async def test_invalid_output_type_raises(self) -> None:
        mock_registry = MagicMock()
        mock_registry.has.return_value = False

        with patch(_REGISTRY, mock_registry):
            unified = UnifiedDesignPipeline(model="test")
            with pytest.raises(ValueError, match="No pipeline for output_type='invalid'"):
                await unified._execute(
                    output_type="invalid",
                    title="Test",
                    sections=[],
                )

    async def test_kwargs_pass_through(self) -> None:
        mock_pipeline = _mock_sub_pipeline()

        mock_registry = MagicMock()
        mock_registry.has.return_value = True
        mock_registry.create.return_value = mock_pipeline

        with patch(_REGISTRY, mock_registry):
            unified = UnifiedDesignPipeline(model="test")
            await unified._execute(
                output_type="presentation",
                title="My Title",
                sections=[{"heading": "Intro"}],
                audience="Executives",
                template_path="/tmp/t.pptx",
            )

        # Verify all kwargs were passed through to the sub-pipeline
        call_kwargs = mock_pipeline._execute.call_args[1]
        assert call_kwargs["title"] == "My Title"
        assert call_kwargs["audience"] == "Executives"
        assert call_kwargs["template_path"] == "/tmp/t.pptx"


# ── Tool registration ──────────────────────────────────────────────────────


class TestRegistration:
    def test_tool_registered(self) -> None:
        from firefly_dworkers.tools.registry import tool_registry

        assert tool_registry.has("unified_design_pipeline")
        assert tool_registry.get_category("unified_design_pipeline") == "design"

    def test_tool_class_correct(self) -> None:
        from firefly_dworkers.tools.registry import tool_registry

        cls = tool_registry.get_class("unified_design_pipeline")
        assert cls is UnifiedDesignPipeline
