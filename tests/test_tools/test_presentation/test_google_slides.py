"""Tests for GoogleSlidesTool adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.presentation.base import PresentationTool
from firefly_dworkers.tools.presentation.google_slides import GoogleSlidesTool
from firefly_dworkers.tools.registry import tool_registry


class TestGoogleSlidesToolRegistration:
    def test_is_presentation_tool(self) -> None:
        assert issubclass(GoogleSlidesTool, PresentationTool)

    def test_is_base_tool(self) -> None:
        assert issubclass(GoogleSlidesTool, BaseTool)

    def test_registry_entry(self) -> None:
        assert tool_registry.has("google_slides")
        assert tool_registry.get_class("google_slides") is GoogleSlidesTool

    def test_category(self) -> None:
        assert tool_registry.get_category("google_slides") == "presentation"

    def test_name(self) -> None:
        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        assert tool.name == "google_slides"


class TestGoogleSlidesToolAuth:
    def test_requires_credentials(self) -> None:
        tool = GoogleSlidesTool()  # No credentials
        with pytest.raises((ConnectorAuthError, ImportError)):
            tool._get_service()

    def test_service_account_key_path(self) -> None:
        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        assert tool._service_account_key == "/fake/key.json"

    def test_credentials_json(self) -> None:
        tool = GoogleSlidesTool(credentials_json='{"type": "service_account"}')
        assert tool._credentials_json == '{"type": "service_account"}'


class TestGoogleSlidesToolRead:
    async def test_read_presentation_mocked(self) -> None:
        """Test read with mocked Google API."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.get.return_value.execute.return_value = {
            "slides": [
                {
                    "pageElements": [
                        {
                            "shape": {
                                "placeholder": {"type": "TITLE"},
                                "text": {
                                    "textElements": [
                                        {"textRun": {"content": "Test Slide"}}
                                    ]
                                },
                            }
                        }
                    ],
                    "slideProperties": {"layoutObjectId": "layout1"},
                }
            ],
            "layouts": [
                {"layoutProperties": {"displayName": "Title Slide"}}
            ],
            "pageSize": {
                "width": {"magnitude": 9144000},
                "height": {"magnitude": 6858000},
            },
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        result = await tool._read_presentation("fake-presentation-id")
        assert len(result.slides) == 1
        assert result.slides[0].title == "Test Slide"
        assert "Title Slide" in result.master_layouts


class TestGoogleSlidesToolCreate:
    async def test_create_presentation_mocked(self) -> None:
        """Test create with mocked Google API."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "new-pres-id",
        }
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        from firefly_dworkers.tools.presentation.models import SlideSpec

        slides = [SlideSpec(title="Hello", content="World")]
        result = await tool._create_presentation("", slides)
        assert result == b"new-pres-id"


class TestGoogleSlidesToolModify:
    async def test_modify_presentation_add_slide(self) -> None:
        """Test modify with add_slide operation."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {}

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        from firefly_dworkers.tools.presentation.models import SlideOperation

        ops = [SlideOperation(operation="add_slide", data={"layout": "BLANK"})]
        result = await tool._modify_presentation("pres-id", ops)
        assert result == b"pres-id"
