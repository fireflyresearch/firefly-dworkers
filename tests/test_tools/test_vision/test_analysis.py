"""Tests for VisionAnalysisTool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.vision.analysis import VisionAnalysisTool

# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestVisionAnalysisToolRegistration:
    def test_is_base_tool(self) -> None:
        assert issubclass(VisionAnalysisTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("vision_analysis")
        assert tool_registry.get_class("vision_analysis") is VisionAnalysisTool

    def test_category(self) -> None:
        assert tool_registry.get_category("vision_analysis") == "vision"

    def test_name(self) -> None:
        assert VisionAnalysisTool().name == "vision_analysis"


# ---------------------------------------------------------------------------
# Analyze action tests
# ---------------------------------------------------------------------------


class TestVisionAnalysisToolAnalyze:
    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    async def test_analyze_returns_analysis(self, mock_agent_cls: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.output = "The image shows a bar chart with quarterly revenue."
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result
        mock_agent_cls.return_value = mock_agent

        tool = VisionAnalysisTool()
        result = await tool.execute(
            action="analyze",
            image_path="/tmp/test.png",
            prompt="Describe this image",
        )
        assert result["analysis"] == "The image shows a bar chart with quarterly revenue."
        assert result["image_path"] == "/tmp/test.png"

    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    async def test_analyze_normalizes_local_path(self, mock_agent_cls: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.output = "analysis"
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result
        mock_agent_cls.return_value = mock_agent

        tool = VisionAnalysisTool()
        await tool.execute(
            action="analyze",
            image_path="/tmp/test.png",
            prompt="Describe",
        )

        # Verify the agent received a file:// URL for the local path
        call_args = mock_agent.run.call_args
        prompt_parts = call_args[0][0]
        image_part = prompt_parts[1]
        assert image_part.url.startswith("file:///")
        assert image_part.url.endswith("/tmp/test.png")

    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    async def test_analyze_preserves_url(self, mock_agent_cls: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.output = "analysis"
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result
        mock_agent_cls.return_value = mock_agent

        tool = VisionAnalysisTool()
        await tool.execute(
            action="analyze",
            image_path="https://example.com/img.png",
            prompt="Describe",
        )

        call_args = mock_agent.run.call_args
        prompt_parts = call_args[0][0]
        image_part = prompt_parts[1]
        assert image_part.url == "https://example.com/img.png"

    async def test_analyze_missing_image_path_raises(self) -> None:
        tool = VisionAnalysisTool()
        with pytest.raises(ToolError, match="image_path"):
            await tool.execute(action="analyze", prompt="Describe")


# ---------------------------------------------------------------------------
# Compare action tests
# ---------------------------------------------------------------------------


class TestVisionAnalysisToolCompare:
    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    async def test_compare_returns_comparison(self, mock_agent_cls: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.output = "Image A shows a pie chart while Image B shows a bar chart."
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result
        mock_agent_cls.return_value = mock_agent

        tool = VisionAnalysisTool()
        result = await tool.execute(
            action="compare",
            image_a="/tmp/a.png",
            image_b="/tmp/b.png",
            prompt="Compare these images",
        )
        assert result["comparison"] == "Image A shows a pie chart while Image B shows a bar chart."
        assert result["image_a"] == "/tmp/a.png"
        assert result["image_b"] == "/tmp/b.png"

    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    async def test_compare_passes_two_images(self, mock_agent_cls: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.output = "comparison"
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result
        mock_agent_cls.return_value = mock_agent

        tool = VisionAnalysisTool()
        await tool.execute(
            action="compare",
            image_a="/tmp/a.png",
            image_b="/tmp/b.png",
            prompt="Compare",
        )

        call_args = mock_agent.run.call_args
        prompt_parts = call_args[0][0]
        # Should be: [prompt_text, ImageUrl_a, ImageUrl_b]
        assert len(prompt_parts) == 3


# ---------------------------------------------------------------------------
# Render and analyze tests
# ---------------------------------------------------------------------------


class TestVisionAnalysisToolRenderAndAnalyze:
    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    async def test_render_and_analyze_with_image_file(self, mock_agent_cls: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.output = "The slide contains a title and bullet points."
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_result
        mock_agent_cls.return_value = mock_agent

        tool = VisionAnalysisTool()
        result = await tool.execute(
            action="render_and_analyze",
            document_path="/tmp/slide.png",
            prompt="Describe the slide",
        )
        # Should delegate to analyze since the path is already an image
        assert result["analysis"] == "The slide contains a title and bullet points."

    async def test_render_and_analyze_with_non_image_raises(self) -> None:
        tool = VisionAnalysisTool()
        with pytest.raises(ToolError, match="pre-rendered image"):
            await tool.execute(
                action="render_and_analyze",
                document_path="/tmp/report.pptx",
                prompt="Describe",
            )


# ---------------------------------------------------------------------------
# Invalid action
# ---------------------------------------------------------------------------


class TestVisionAnalysisToolInvalidAction:
    async def test_unknown_action_raises(self) -> None:
        tool = VisionAnalysisTool()
        with pytest.raises(ToolError, match="Unknown action"):
            await tool.execute(action="transcribe", prompt="test")


# ---------------------------------------------------------------------------
# Lazy agent init and custom model
# ---------------------------------------------------------------------------


class TestVisionAnalysisToolAgentInit:
    def test_agent_created_lazily(self) -> None:
        tool = VisionAnalysisTool()
        assert tool._agent is None

    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    def test_custom_vision_model(self, mock_agent_cls: MagicMock) -> None:
        tool = VisionAnalysisTool(vision_model="openai:gpt-4o")
        tool._get_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["model"] == "openai:gpt-4o"

    @patch("firefly_dworkers.tools.vision.analysis.FireflyAgent")
    def test_default_model_passes_none(self, mock_agent_cls: MagicMock) -> None:
        tool = VisionAnalysisTool()
        tool._get_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert call_kwargs["model"] is None
