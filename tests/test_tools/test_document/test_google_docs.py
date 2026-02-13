"""Tests for GoogleDocsTool adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.document.base import DocumentTool
from firefly_dworkers.tools.document.google_docs import GoogleDocsTool
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

        from firefly_dworkers.tools.document.models import SectionSpec

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
