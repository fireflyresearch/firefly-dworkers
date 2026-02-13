"""Tests for GoogleSlidesTool adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.design.models import ImagePlacement, TextStyle
from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.presentation.base import PresentationTool
from firefly_dworkers.tools.presentation.google_slides import (
    GoogleSlidesTool,
    _build_text_style_request,
    _hex_to_rgb,
)
from firefly_dworkers.tools.presentation.models import SlideSpec
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


class TestHexToRgb:
    def test_standard_hex(self) -> None:
        result = _hex_to_rgb("#FF0000")
        assert abs(result["red"] - 1.0) < 0.01
        assert abs(result["green"]) < 0.01
        assert abs(result["blue"]) < 0.01

    def test_no_hash(self) -> None:
        result = _hex_to_rgb("00FF00")
        assert abs(result["green"] - 1.0) < 0.01

    def test_short_hex(self) -> None:
        result = _hex_to_rgb("#F00")
        assert abs(result["red"] - 1.0) < 0.01

    def test_mixed_color(self) -> None:
        result = _hex_to_rgb("#1A73E8")
        assert 0.0 < result["red"] < 0.2
        assert 0.4 < result["green"] < 0.5
        assert 0.9 < result["blue"] < 1.0


class TestBuildTextStyleRequest:
    def test_with_all_fields(self) -> None:
        style = TextStyle(font_name="Arial", font_size=14, bold=True, italic=True, color="#FF0000")
        result = _build_text_style_request("obj1", style)
        assert "updateTextStyle" in result
        req = result["updateTextStyle"]
        assert req["objectId"] == "obj1"
        assert req["style"]["fontFamily"] == "Arial"
        assert req["style"]["fontSize"]["magnitude"] == 14
        assert req["style"]["bold"] is True
        assert req["style"]["italic"] is True
        assert "foregroundColor" in req["style"]
        assert "fontFamily" in req["fields"]
        assert "fontSize" in req["fields"]
        assert "bold" in req["fields"]
        assert "italic" in req["fields"]
        assert "foregroundColor" in req["fields"]
        assert req["textRange"]["type"] == "ALL"

    def test_with_font_only(self) -> None:
        style = TextStyle(font_name="Roboto")
        result = _build_text_style_request("obj2", style)
        req = result["updateTextStyle"]
        assert req["style"]["fontFamily"] == "Roboto"
        assert req["fields"] == "fontFamily"

    def test_empty_style_returns_empty(self) -> None:
        style = TextStyle()
        result = _build_text_style_request("obj3", style)
        assert result == {}

    def test_non_textstyle_returns_empty(self) -> None:
        result = _build_text_style_request("obj4", "not a style")
        assert result == {}


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
                                "text": {"textElements": [{"textRun": {"content": "Test Slide"}}]},
                            }
                        }
                    ],
                    "slideProperties": {"layoutObjectId": "layout1"},
                }
            ],
            "layouts": [{"layoutProperties": {"displayName": "Title Slide"}}],
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
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createSlide": {"objectId": "slide_1"}}],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [SlideSpec(title="Hello", content="World")]
        result = await tool._create_presentation("", slides)
        assert result == b"new-pres-id"

    async def test_create_with_title_style(self) -> None:
        """Test that title styling produces updateTextStyle batch requests."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "styled-pres",
        }
        # First batchUpdate creates slides, second applies styling
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createSlide": {"objectId": "slide_abc"}}],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [
            SlideSpec(
                title="Styled",
                title_style=TextStyle(font_name="Arial", font_size=24, bold=True, color="#1A73E8"),
            )
        ]
        result = await tool._create_presentation("", slides)
        assert result == b"styled-pres"

        # batchUpdate should be called twice: once for createSlide, once for styling
        batch_calls = mock_service.presentations.return_value.batchUpdate.call_args_list
        assert len(batch_calls) >= 2

        # Second call should contain styling requests
        styling_body = batch_calls[1][1]["body"] if "body" in batch_calls[1][1] else batch_calls[1][0][0]
        if isinstance(styling_body, dict):
            styling_requests = styling_body.get("requests", [])
        else:
            styling_requests = []

        # Find updateTextStyle requests
        text_style_reqs = [r for r in styling_requests if "updateTextStyle" in r]
        assert len(text_style_reqs) >= 1
        style_req = text_style_reqs[0]["updateTextStyle"]
        assert style_req["objectId"] == "slide_abc_title"
        assert style_req["style"]["fontFamily"] == "Arial"
        assert style_req["style"]["bold"] is True

    async def test_create_with_body_style(self) -> None:
        """Test that body styling produces updateTextStyle batch requests."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "body-styled-pres",
        }
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createSlide": {"objectId": "slide_xyz"}}],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [
            SlideSpec(
                title="Test",
                body_style=TextStyle(font_name="Roboto", font_size=12, italic=True),
            )
        ]
        result = await tool._create_presentation("", slides)
        assert result == b"body-styled-pres"

        batch_calls = mock_service.presentations.return_value.batchUpdate.call_args_list
        assert len(batch_calls) >= 2

        styling_body = batch_calls[1][1]["body"]
        styling_requests = styling_body.get("requests", [])
        text_style_reqs = [r for r in styling_requests if "updateTextStyle" in r]
        assert len(text_style_reqs) >= 1
        body_req = text_style_reqs[0]["updateTextStyle"]
        assert body_req["objectId"] == "slide_xyz_body"
        assert body_req["style"]["fontFamily"] == "Roboto"
        assert body_req["style"]["italic"] is True

    async def test_create_with_background_color(self) -> None:
        """Test that background_color produces updatePageProperties request."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "bg-pres",
        }
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createSlide": {"objectId": "slide_bg"}}],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [SlideSpec(title="BG", background_color="#003366")]
        result = await tool._create_presentation("", slides)
        assert result == b"bg-pres"

        batch_calls = mock_service.presentations.return_value.batchUpdate.call_args_list
        assert len(batch_calls) >= 2

        styling_body = batch_calls[1][1]["body"]
        styling_requests = styling_body.get("requests", [])
        bg_reqs = [r for r in styling_requests if "updatePageProperties" in r]
        assert len(bg_reqs) == 1
        bg_req = bg_reqs[0]["updatePageProperties"]
        assert bg_req["objectId"] == "slide_bg"
        rgb = bg_req["pageProperties"]["pageBackgroundFill"]["solidFill"]["color"]["rgbColor"]
        assert abs(rgb["red"] - 0.0) < 0.01
        assert abs(rgb["green"] - 0.2) < 0.01
        assert abs(rgb["blue"] - 0.4) < 0.01

    async def test_create_with_images(self) -> None:
        """Test that images produce createImage batch requests."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "img-pres",
        }
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createSlide": {"objectId": "slide_img"}}],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [
            SlideSpec(
                title="Images",
                images=[
                    ImagePlacement(
                        image_ref="https://example.com/photo.png",
                        width=300,
                        height=200,
                    ),
                ],
            )
        ]
        result = await tool._create_presentation("", slides)
        assert result == b"img-pres"

        batch_calls = mock_service.presentations.return_value.batchUpdate.call_args_list
        assert len(batch_calls) >= 2

        styling_body = batch_calls[1][1]["body"]
        styling_requests = styling_body.get("requests", [])
        img_reqs = [r for r in styling_requests if "createImage" in r]
        assert len(img_reqs) == 1
        img_req = img_reqs[0]["createImage"]
        assert img_req["url"] == "https://example.com/photo.png"
        assert img_req["elementProperties"]["pageObjectId"] == "slide_img"
        assert img_req["elementProperties"]["size"]["width"]["magnitude"] == 300
        assert img_req["elementProperties"]["size"]["height"]["magnitude"] == 200

    async def test_create_with_image_position(self) -> None:
        """Test that image positions produce transform in the request."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "pos-pres",
        }
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createSlide": {"objectId": "slide_pos"}}],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [
            SlideSpec(
                title="Positioned",
                images=[
                    ImagePlacement(
                        image_ref="https://example.com/img.png",
                        left=50,
                        top=100,
                    ),
                ],
            )
        ]
        await tool._create_presentation("", slides)

        batch_calls = mock_service.presentations.return_value.batchUpdate.call_args_list
        styling_body = batch_calls[1][1]["body"]
        styling_requests = styling_body.get("requests", [])
        img_reqs = [r for r in styling_requests if "createImage" in r]
        assert len(img_reqs) == 1
        transform = img_reqs[0]["createImage"]["elementProperties"]["transform"]
        assert transform["translateX"] == 50
        assert transform["translateY"] == 100

    async def test_create_without_enhancements_no_style_batch(self) -> None:
        """Test that slides without styling don't trigger a second batchUpdate."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "plain-pres",
        }
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"createSlide": {"objectId": "slide_plain"}}],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [SlideSpec(title="Plain", content="No styling")]
        result = await tool._create_presentation("", slides)
        assert result == b"plain-pres"

        # Only one batchUpdate call (for createSlide), no styling call
        batch_calls = mock_service.presentations.return_value.batchUpdate.call_args_list
        assert len(batch_calls) == 1

    async def test_create_multiple_slides_with_mixed_features(self) -> None:
        """Test creating multiple slides with different enhancement features."""
        mock_service = MagicMock()
        mock_service.presentations.return_value.create.return_value.execute.return_value = {
            "presentationId": "multi-pres",
        }
        mock_service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [
                {"createSlide": {"objectId": "slide_1"}},
                {"createSlide": {"objectId": "slide_2"}},
            ],
        }

        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        tool._service = mock_service

        slides = [
            SlideSpec(
                title="First",
                title_style=TextStyle(font_name="Arial", bold=True),
                background_color="#FFFFFF",
            ),
            SlideSpec(
                title="Second",
                images=[ImagePlacement(image_ref="https://example.com/img.png")],
            ),
        ]
        result = await tool._create_presentation("", slides)
        assert result == b"multi-pres"

        batch_calls = mock_service.presentations.return_value.batchUpdate.call_args_list
        assert len(batch_calls) >= 2

        styling_body = batch_calls[1][1]["body"]
        styling_requests = styling_body.get("requests", [])
        # Should have: 1 updatePageProperties + 1 updateTextStyle + 1 createImage = 3
        assert len(styling_requests) == 3


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


class TestBuildSlideEnhancementRequests:
    def test_empty_slides_returns_empty(self) -> None:
        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        result = tool._build_slide_enhancement_requests([], [], {})
        assert result == []

    def test_no_enhancements_returns_empty(self) -> None:
        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        result = tool._build_slide_enhancement_requests(
            [SlideSpec(title="Plain")],
            ["slide_1"],
            {},
        )
        assert result == []

    def test_slide_id_missing_skips(self) -> None:
        tool = GoogleSlidesTool(service_account_key="/fake/key.json")
        result = tool._build_slide_enhancement_requests(
            [SlideSpec(title="X", background_color="#000000")],
            [],  # no slide IDs
            {},
        )
        assert result == []
