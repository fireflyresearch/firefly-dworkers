"""Tests for PDFTool."""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock, patch

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.document.pdf import PDFTool, _PROFESSIONAL_CSS
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
        html = PDFTool._markdown_to_html("# Title")
        assert "<h1>" in html
        assert "Title" in html

    def test_h2_conversion(self) -> None:
        html = PDFTool._markdown_to_html("## Subtitle")
        assert "<h2>" in html
        assert "Subtitle" in html

    def test_h3_conversion(self) -> None:
        html = PDFTool._markdown_to_html("### Sub-subtitle")
        assert "<h3>" in html
        assert "Sub-subtitle" in html

    def test_bold_conversion(self) -> None:
        html = PDFTool._markdown_to_html("This is **bold** text.")
        assert "<strong>bold</strong>" in html

    def test_italic_conversion(self) -> None:
        html = PDFTool._markdown_to_html("This is *italic* text.")
        assert "<em>italic</em>" in html

    def test_paragraph_wrapping(self) -> None:
        html = PDFTool._markdown_to_html("A paragraph.\n\nAnother paragraph.")
        assert "<p>" in html


class TestPDFToolMarkdownRegexFallback:
    """Test the regex fallback directly (always available)."""

    def test_heading_regex(self) -> None:
        html = PDFTool._markdown_to_html_regex("# Title")
        assert "<h1>Title</h1>" in html

    def test_h2_regex(self) -> None:
        html = PDFTool._markdown_to_html_regex("## Subtitle")
        assert "<h2>Subtitle</h2>" in html

    def test_h3_regex(self) -> None:
        html = PDFTool._markdown_to_html_regex("### Sub-subtitle")
        assert "<h3>Sub-subtitle</h3>" in html

    def test_bold_regex(self) -> None:
        html = PDFTool._markdown_to_html_regex("This is **bold** text.")
        assert "<strong>bold</strong>" in html

    def test_italic_regex(self) -> None:
        html = PDFTool._markdown_to_html_regex("This is *italic* text.")
        assert "<em>italic</em>" in html

    def test_paragraph_regex(self) -> None:
        html = PDFTool._markdown_to_html_regex("Hello world.\n\nAnother paragraph.")
        assert "<p>Hello world.</p>" in html
        assert "<p>Another paragraph.</p>" in html

    def test_html_passthrough_regex(self) -> None:
        """Elements that already look like HTML are not re-wrapped."""
        html = PDFTool._markdown_to_html_regex("<div>keep</div>")
        assert "<p>" not in html
        assert "<div>keep</div>" in html


class TestPDFToolMarkdownLibraryPreferred:
    """Ensure the markdown library is preferred when available."""

    def test_uses_markdown_library_when_available(self) -> None:
        mock_markdown = MagicMock()
        mock_markdown.markdown.return_value = "<p>converted</p>"
        with patch.dict("sys.modules", {"markdown": mock_markdown}):
            # Clear any cached import so the try/import picks up the mock
            result = PDFTool._markdown_to_html("# Hello")
            mock_markdown.markdown.assert_called_once_with(
                "# Hello", extensions=["tables", "fenced_code"]
            )
            assert result == "<p>converted</p>"

    def test_falls_back_to_regex_when_markdown_unavailable(self) -> None:
        with patch.dict("sys.modules", {"markdown": None}):
            html = PDFTool._markdown_to_html("# Hello")
            assert "<h1>Hello</h1>" in html


class TestPDFToolProfessionalCSS:
    """Test professional CSS defaults."""

    def test_professional_css_constant_has_body(self) -> None:
        assert "body" in _PROFESSIONAL_CSS
        assert "font-family" in _PROFESSIONAL_CSS

    def test_professional_css_has_table_styles(self) -> None:
        assert "table" in _PROFESSIONAL_CSS
        assert "border-collapse" in _PROFESSIONAL_CSS

    def test_professional_css_has_heading_styles(self) -> None:
        assert "h1" in _PROFESSIONAL_CSS
        assert "h2" in _PROFESSIONAL_CSS
        assert "h3" in _PROFESSIONAL_CSS

    def test_professional_css_has_code_styles(self) -> None:
        assert "code" in _PROFESSIONAL_CSS
        assert "pre" in _PROFESSIONAL_CSS

    def test_professional_css_accessor(self) -> None:
        """The public accessor returns the same CSS constant."""
        assert PDFTool.professional_css() == _PROFESSIONAL_CSS

    def test_default_css_applied_when_none_provided(self) -> None:
        """When no custom CSS is given, _generate_sync should use professional CSS."""
        tool = PDFTool()
        # We can't call _generate_sync without weasyprint, but we can verify
        # the constructor default: when default_css="" the _generate_sync will
        # use _PROFESSIONAL_CSS as effective_css.
        assert tool._default_css == ""

    def test_custom_default_css_overrides(self) -> None:
        """When default_css is provided, it's stored for use."""
        tool = PDFTool(default_css="body { color: red; }")
        assert tool._default_css == "body { color: red; }"


class TestPDFToolEmbedImage:
    """Test embed_image() static method (no weasyprint needed)."""

    def test_embed_image_returns_img_tag(self) -> None:
        img_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Fake PNG-ish bytes
        result = PDFTool.embed_image(img_bytes)
        assert result.startswith("<img ")
        assert 'src="data:image/png;base64,' in result
        assert result.endswith('" />')

    def test_embed_image_base64_roundtrip(self) -> None:
        original = b"test image data here"
        result = PDFTool.embed_image(original)
        # Extract base64 from the tag
        b64_start = result.index("base64,") + len("base64,")
        b64_end = result.index('"', b64_start)
        decoded = base64.b64decode(result[b64_start:b64_end])
        assert decoded == original

    def test_embed_image_custom_mime_type(self) -> None:
        result = PDFTool.embed_image(b"data", mime_type="image/jpeg")
        assert 'data:image/jpeg;base64,' in result

    def test_embed_image_alt_text(self) -> None:
        result = PDFTool.embed_image(b"data", alt="My Chart")
        assert 'alt="My Chart"' in result

    def test_embed_image_default_alt_empty(self) -> None:
        result = PDFTool.embed_image(b"data")
        assert 'alt=""' in result

    def test_embed_image_empty_bytes(self) -> None:
        result = PDFTool.embed_image(b"")
        assert 'src="data:image/png;base64,"' in result


class TestPDFToolEmbedChartImage:
    """Test embed_chart_image() static method."""

    def test_embed_chart_image_renders_and_returns_img_tag(self) -> None:
        """embed_chart_image should use ChartRenderer and return an img tag."""
        fake_png = b"\x89PNGfakedata"
        mock_chart = MagicMock()
        mock_chart.title = "Revenue Chart"

        mock_renderer_instance = MagicMock()
        mock_renderer_instance.render_to_image_sync.return_value = fake_png

        with patch(
            "firefly_dworkers.design.charts.ChartRenderer",
            return_value=mock_renderer_instance,
        ) as mock_renderer_cls:
            result = PDFTool.embed_chart_image(mock_chart)

        mock_renderer_cls.assert_called_once_with()
        mock_renderer_instance.render_to_image_sync.assert_called_once_with(mock_chart)
        assert "<img " in result
        assert 'alt="Revenue Chart"' in result
        assert "base64," in result

    def test_embed_chart_image_uses_chart_title_as_alt(self) -> None:
        mock_chart = MagicMock()
        mock_chart.title = "Sales Growth"

        mock_renderer = MagicMock()
        mock_renderer.render_to_image_sync.return_value = b"png"

        with patch(
            "firefly_dworkers.design.charts.ChartRenderer",
            return_value=mock_renderer,
        ):
            result = PDFTool.embed_chart_image(mock_chart)

        assert 'alt="Sales Growth"' in result

    def test_embed_chart_image_fallback_alt_when_no_title(self) -> None:
        mock_chart = MagicMock()
        mock_chart.title = ""

        mock_renderer = MagicMock()
        mock_renderer.render_to_image_sync.return_value = b"png"

        with patch(
            "firefly_dworkers.design.charts.ChartRenderer",
            return_value=mock_renderer,
        ):
            result = PDFTool.embed_chart_image(mock_chart)

        assert 'alt="Chart"' in result


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

    async def test_professional_css_applied_by_default(self) -> None:
        """When no CSS is provided, professional CSS should be applied."""
        pytest.importorskip("weasyprint")
        tool = PDFTool()
        # generate should succeed with professional CSS applied automatically
        result = await tool.execute(
            action="generate",
            content="# Report\n\nProfessionally styled content.",
            content_type="markdown",
        )
        assert result["success"] is True
        assert result["bytes_length"] > 0


class TestPDFToolPublicAPI:
    async def test_artifact_bytes_none_initially(self) -> None:
        assert PDFTool().artifact_bytes is None

    async def test_artifact_bytes_after_execute(self) -> None:
        pytest.importorskip("weasyprint")
        tool = PDFTool()
        await tool.execute(action="generate", content="# Hello")
        assert tool.artifact_bytes is not None
        assert len(tool.artifact_bytes) > 0

    async def test_generate_returns_bytes(self) -> None:
        pytest.importorskip("weasyprint")
        tool = PDFTool()
        result = await tool.generate("# Hello")
        assert isinstance(result, bytes)
        assert len(result) > 0

    async def test_generate_and_save(self, tmp_path) -> None:
        pytest.importorskip("weasyprint")
        tool = PDFTool()
        out = str(tmp_path / "test.pdf")
        path = await tool.generate_and_save(out, "# Hello")
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
