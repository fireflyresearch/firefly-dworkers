"""Tests for GoogleDocsTool adapter."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.design.models import TextStyle
from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.document.base import DocumentTool
from firefly_dworkers.tools.document.google_docs import (
    GoogleDocsTool,
    _build_docs_text_style,
    _hex_to_rgb_docs,
)
from firefly_dworkers.tools.document.models import SectionSpec
from firefly_dworkers.tools.registry import tool_registry


class TestGoogleDocsToolRegistration:
    def test_is_document_tool(self) -> None:
        assert issubclass(GoogleDocsTool, DocumentTool)

    def test_is_base_tool(self) -> None:
        assert issubclass(GoogleDocsTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("google_docs")
        assert tool_registry.get_class("google_docs") is GoogleDocsTool

    def test_category(self) -> None:
        assert tool_registry.get_category("google_docs") == "document"

    def test_name(self) -> None:
        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        assert tool.name == "google_docs"


class TestGoogleDocsToolAuth:
    def test_requires_credentials(self) -> None:
        tool = GoogleDocsTool()
        with pytest.raises((ConnectorAuthError, ImportError)):
            tool._get_service()

    def test_service_account_key_path(self) -> None:
        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        assert tool._service_account_key == "/fake/key.json"

    def test_credentials_json(self) -> None:
        tool = GoogleDocsTool(credentials_json='{"type": "service_account"}')
        assert tool._credentials_json == '{"type": "service_account"}'


class TestHexToRgbDocs:
    def test_full_hex(self) -> None:
        result = _hex_to_rgb_docs("#0000FF")
        assert abs(result["red"]) < 0.01
        assert abs(result["green"]) < 0.01
        assert abs(result["blue"] - 1.0) < 0.01

    def test_short_hex(self) -> None:
        result = _hex_to_rgb_docs("#0F0")
        assert abs(result["green"] - 1.0) < 0.01

    def test_no_hash(self) -> None:
        result = _hex_to_rgb_docs("FF0000")
        assert abs(result["red"] - 1.0) < 0.01


class TestBuildDocsTextStyle:
    def test_all_fields(self) -> None:
        style = TextStyle(font_name="Georgia", font_size=16, bold=True, italic=True, color="#333333")
        text_style, fields = _build_docs_text_style(style)
        assert text_style["weightedFontFamily"]["fontFamily"] == "Georgia"
        assert text_style["fontSize"]["magnitude"] == 16
        assert text_style["bold"] is True
        assert text_style["italic"] is True
        assert "foregroundColor" in text_style
        assert set(fields) == {"weightedFontFamily", "fontSize", "bold", "italic", "foregroundColor"}

    def test_font_only(self) -> None:
        style = TextStyle(font_name="Courier")
        text_style, fields = _build_docs_text_style(style)
        assert text_style["weightedFontFamily"]["fontFamily"] == "Courier"
        assert fields == ["weightedFontFamily"]

    def test_empty_style(self) -> None:
        style = TextStyle()
        text_style, fields = _build_docs_text_style(style)
        assert text_style == {}
        assert fields == []

    def test_non_textstyle(self) -> None:
        text_style, fields = _build_docs_text_style("not a style")
        assert text_style == {}
        assert fields == []


class TestGoogleDocsToolRead:
    async def test_read_document_mocked(self) -> None:
        mock_service = MagicMock()
        mock_service.documents.return_value.get.return_value.execute.return_value = {
            "title": "Test Document",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Introduction\n"}}],
                            "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "This is a paragraph.\n"}}],
                            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        }
                    },
                ]
            },
        }

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._read_document("fake-doc-id")
        assert result.title == "Test Document"
        assert len(result.paragraphs) == 2
        assert result.paragraphs[0].is_heading is True
        assert result.paragraphs[0].heading_level == 1
        assert result.paragraphs[0].text == "Introduction"
        assert result.paragraphs[1].is_heading is False
        assert result.paragraphs[1].text == "This is a paragraph."

    async def test_read_document_skips_empty_paragraphs(self) -> None:
        mock_service = MagicMock()
        mock_service.documents.return_value.get.return_value.execute.return_value = {
            "title": "Doc",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "\n"}}],
                            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Actual content\n"}}],
                            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        }
                    },
                ]
            },
        }

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._read_document("doc-id")
        assert len(result.paragraphs) == 1
        assert result.paragraphs[0].text == "Actual content"

    async def test_read_document_non_paragraph_elements_skipped(self) -> None:
        mock_service = MagicMock()
        mock_service.documents.return_value.get.return_value.execute.return_value = {
            "title": "Doc",
            "body": {
                "content": [
                    {"sectionBreak": {}},
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Hello\n"}}],
                            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                        }
                    },
                ]
            },
        }

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._read_document("doc-id")
        assert len(result.paragraphs) == 1
        assert result.paragraphs[0].text == "Hello"


class TestGoogleDocsToolCreate:
    async def test_create_document_mocked(self) -> None:
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "new-doc-id",
        }
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sections = [SectionSpec(heading="Intro", heading_level=1, content="Body text")]
        result = await tool._create_document("My Doc", sections)
        assert result == b"new-doc-id"

    async def test_create_document_no_sections(self) -> None:
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "empty-doc-id",
        }

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._create_document("Empty Doc", [])
        assert result == b"empty-doc-id"
        # batchUpdate should not be called when there are no sections
        mock_service.documents.return_value.batchUpdate.assert_not_called()

    async def test_create_with_heading_style(self) -> None:
        """Test that heading_style produces updateTextStyle requests."""
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "styled-doc",
        }
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sections = [
            SectionSpec(
                heading="Title",
                heading_level=1,
                heading_style=TextStyle(font_name="Georgia", font_size=28, bold=True, color="#1A73E8"),
            )
        ]
        result = await tool._create_document("Styled", sections)
        assert result == b"styled-doc"

        # Verify batch update was called
        batch_calls = mock_service.documents.return_value.batchUpdate.call_args_list
        assert len(batch_calls) == 1

        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        # Should have: insertText, updateParagraphStyle, updateTextStyle
        text_style_reqs = [r for r in reqs if "updateTextStyle" in r]
        assert len(text_style_reqs) == 1
        style_req = text_style_reqs[0]["updateTextStyle"]
        assert style_req["textStyle"]["weightedFontFamily"]["fontFamily"] == "Georgia"
        assert style_req["textStyle"]["fontSize"]["magnitude"] == 28
        assert style_req["textStyle"]["bold"] is True
        assert "foregroundColor" in style_req["textStyle"]
        # Range should cover the heading text (index 1 to 1+len("Title")=6)
        assert style_req["range"]["startIndex"] == 1
        assert style_req["range"]["endIndex"] == 6

    async def test_create_with_body_style(self) -> None:
        """Test that body_style produces updateTextStyle requests on content."""
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "body-styled-doc",
        }
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sections = [
            SectionSpec(
                heading="Head",
                heading_level=1,
                content="Body text here",
                body_style=TextStyle(font_name="Roboto", font_size=12, italic=True),
            )
        ]
        result = await tool._create_document("Doc", sections)
        assert result == b"body-styled-doc"

        batch_calls = mock_service.documents.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        text_style_reqs = [r for r in reqs if "updateTextStyle" in r]
        assert len(text_style_reqs) == 1
        style_req = text_style_reqs[0]["updateTextStyle"]
        assert style_req["textStyle"]["weightedFontFamily"]["fontFamily"] == "Roboto"
        assert style_req["textStyle"]["italic"] is True
        # Content starts after heading "Head\n" (index 1+5=6)
        assert style_req["range"]["startIndex"] == 6
        # Content end = 6 + len("Body text here") = 20
        assert style_req["range"]["endIndex"] == 20

    async def test_create_with_numbered_list(self) -> None:
        """Test that numbered_list produces createParagraphBullets request."""
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "list-doc",
        }
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sections = [
            SectionSpec(
                numbered_list=["First item", "Second item", "Third item"],
            )
        ]
        result = await tool._create_document("List Doc", sections)
        assert result == b"list-doc"

        batch_calls = mock_service.documents.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        # Should have 3 insertText + 1 createParagraphBullets
        insert_reqs = [r for r in reqs if "insertText" in r]
        assert len(insert_reqs) == 3

        bullet_reqs = [r for r in reqs if "createParagraphBullets" in r]
        assert len(bullet_reqs) == 1
        bullet_req = bullet_reqs[0]["createParagraphBullets"]
        assert bullet_req["bulletPreset"] == "NUMBERED_DECIMAL_ALPHA_ROMAN"
        # Range should cover all three items
        assert bullet_req["range"]["startIndex"] == 1
        # 1 + len("First item\n") + len("Second item\n") + len("Third item\n")
        expected_end = 1 + 11 + 12 + 11  # = 35
        assert bullet_req["range"]["endIndex"] == expected_end

    async def test_create_with_callout(self) -> None:
        """Test that callout produces indented paragraph style."""
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "callout-doc",
        }
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sections = [
            SectionSpec(
                callout="Important note: this is a callout",
            )
        ]
        result = await tool._create_document("Callout Doc", sections)
        assert result == b"callout-doc"

        batch_calls = mock_service.documents.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        # Should have insertText + updateParagraphStyle for indentation
        insert_reqs = [r for r in reqs if "insertText" in r]
        assert len(insert_reqs) == 1
        assert insert_reqs[0]["insertText"]["text"] == "Important note: this is a callout\n"

        para_style_reqs = [r for r in reqs if "updateParagraphStyle" in r]
        assert len(para_style_reqs) == 1
        ps = para_style_reqs[0]["updateParagraphStyle"]
        assert ps["paragraphStyle"]["indentFirstLine"]["magnitude"] == 36
        assert ps["paragraphStyle"]["indentStart"]["magnitude"] == 36
        assert "indentFirstLine" in ps["fields"]
        assert "indentStart" in ps["fields"]

    async def test_create_with_all_features(self) -> None:
        """Test creating a section with heading style, body style, numbered list, and callout."""
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "all-features-doc",
        }
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sections = [
            SectionSpec(
                heading="Overview",
                heading_level=2,
                content="Some content",
                heading_style=TextStyle(font_name="Arial", bold=True),
                body_style=TextStyle(font_name="Arial", font_size=11),
                numbered_list=["Step 1", "Step 2"],
                callout="Note: pay attention",
            )
        ]
        result = await tool._create_document("Full Doc", sections)
        assert result == b"all-features-doc"

        batch_calls = mock_service.documents.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        # Verify each type of request is present
        insert_reqs = [r for r in reqs if "insertText" in r]
        assert len(insert_reqs) >= 4  # heading + content + 2 list items + callout = 5

        heading_style_reqs = [r for r in reqs if "updateParagraphStyle" in r and
                              r.get("updateParagraphStyle", {}).get("paragraphStyle", {}).get("namedStyleType")]
        assert len(heading_style_reqs) == 1

        bullet_reqs = [r for r in reqs if "createParagraphBullets" in r]
        assert len(bullet_reqs) == 1

        indent_reqs = [r for r in reqs if "updateParagraphStyle" in r and
                       "indentStart" in r.get("updateParagraphStyle", {}).get("paragraphStyle", {})]
        assert len(indent_reqs) == 1

        text_style_reqs = [r for r in reqs if "updateTextStyle" in r]
        assert len(text_style_reqs) == 2  # heading style + body style

    async def test_create_backwards_compatible_no_enhancements(self) -> None:
        """Test that creating a document without new features works as before."""
        mock_service = MagicMock()
        mock_service.documents.return_value.create.return_value.execute.return_value = {
            "documentId": "compat-doc",
        }
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        sections = [
            SectionSpec(
                heading="Simple",
                heading_level=1,
                content="Just plain text",
                bullet_points=["Point A", "Point B"],
            )
        ]
        result = await tool._create_document("Simple Doc", sections)
        assert result == b"compat-doc"

        batch_calls = mock_service.documents.return_value.batchUpdate.call_args_list
        body = batch_calls[0][1]["body"]
        reqs = body["requests"]

        # No updateTextStyle, no createParagraphBullets, no callout indent
        text_style_reqs = [r for r in reqs if "updateTextStyle" in r]
        assert len(text_style_reqs) == 0

        bullet_reqs = [r for r in reqs if "createParagraphBullets" in r]
        assert len(bullet_reqs) == 0


class TestGoogleDocsToolModify:
    async def test_modify_document_add_section(self) -> None:
        mock_service = MagicMock()
        mock_service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        from firefly_dworkers.tools.document.models import DocumentOperation

        ops = [
            DocumentOperation(
                operation="add_section",
                data={"heading": "New Section", "content": "Section content"},
            )
        ]
        result = await tool._modify_document("doc-id", ops)
        assert result == b"doc-id"

    async def test_modify_document_no_operations(self) -> None:
        mock_service = MagicMock()

        tool = GoogleDocsTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._modify_document("doc-id", [])
        assert result == b"doc-id"
        mock_service.documents.return_value.batchUpdate.assert_not_called()
