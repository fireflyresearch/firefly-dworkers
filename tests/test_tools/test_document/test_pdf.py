"""Tests for PDFTool."""

from __future__ import annotations

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.document.pdf import PDFTool
from firefly_dworkers.tools.registry import tool_registry


class TestPDFToolRegistration:
    def test_is_base_tool(self) -> None:
        assert issubclass(PDFTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("pdf")
        assert tool_registry.get_class("pdf") is PDFTool

    def test_category(self) -> None:
        assert tool_registry.get_category("pdf") == "document"

    def test_name(self) -> None:
        assert PDFTool().name == "pdf"

    def test_tags(self) -> None:
        tags = PDFTool().tags
        assert "pdf" in tags
        assert "document" in tags

    def test_parameters(self) -> None:
        param_names = [p.name for p in PDFTool().parameters]
        assert "action" in param_names
        assert "content" in param_names
        assert "content_type" in param_names
        assert "css" in param_names


class TestPDFToolMarkdownConversion:
    """Test Markdown to HTML conversion (no weasyprint needed)."""

    def test_heading_conversion(self) -> None:
        tool = PDFTool()
        html = tool._markdown_to_html("# Title")
        assert "<h1>Title</h1>" in html

    def test_h2_conversion(self) -> None:
        tool = PDFTool()
        html = tool._markdown_to_html("## Subtitle")
        assert "<h2>Subtitle</h2>" in html

    def test_h3_conversion(self) -> None:
        tool = PDFTool()
        html = tool._markdown_to_html("### Sub-subtitle")
        assert "<h3>Sub-subtitle</h3>" in html

    def test_bold_conversion(self) -> None:
        tool = PDFTool()
        html = tool._markdown_to_html("This is **bold** text.")
        assert "<strong>bold</strong>" in html

    def test_italic_conversion(self) -> None:
        tool = PDFTool()
        html = tool._markdown_to_html("This is *italic* text.")
        assert "<em>italic</em>" in html

    def test_paragraph_wrapping(self) -> None:
        tool = PDFTool()
        html = tool._markdown_to_html("A paragraph.\n\nAnother paragraph.")
        assert "<p>" in html


class TestPDFToolValidation:
    """Test validation logic (no weasyprint needed)."""

    async def test_unknown_action_raises(self) -> None:
        tool = PDFTool()
        with pytest.raises(ToolError, match="Unknown action"):
            await tool.execute(action="delete", content="test")


class TestPDFToolGenerate:
    """Tests requiring weasyprint (may be skipped)."""

    async def test_generate_from_html(self) -> None:
        pytest.importorskip("weasyprint")
        tool = PDFTool()
        result = await tool.execute(
            action="generate",
            content="<h1>Hello</h1><p>World</p>",
            content_type="html",
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_generate_from_markdown(self) -> None:
        pytest.importorskip("weasyprint")
        tool = PDFTool()
        result = await tool.execute(
            action="generate",
            content="# Hello\n\nWorld",
            content_type="markdown",
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0

    async def test_generate_with_css(self) -> None:
        pytest.importorskip("weasyprint")
        tool = PDFTool()
        result = await tool.execute(
            action="generate",
            content="<p>Styled</p>",
            content_type="html",
            css="p { color: blue; }",
        )
        assert result["success"] is True

    async def test_generate_with_default_css(self) -> None:
        pytest.importorskip("weasyprint")
        tool = PDFTool(default_css="body { font-family: sans-serif; }")
        result = await tool.execute(
            action="generate",
            content="<p>Default styled</p>",
            content_type="html",
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0
