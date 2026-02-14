"""Google Slides adapter for PresentationTool.

This adapter uses the Google Slides API v1 for presentation operations.
Install with::

    pip install firefly-dworkers[google]
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError
from firefly_dworkers.tools.presentation.base import PresentationTool
from firefly_dworkers.tools.presentation.models import (
    PresentationData,
    SlideData,
    SlideOperation,
    SlideSpec,
)
from firefly_dworkers.tools.registry import tool_registry

logger = logging.getLogger(__name__)

try:
    from google.oauth2 import service_account as _sa
    from googleapiclient.discovery import build as _build

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


def _hex_to_rgb(hex_color: str) -> dict[str, float]:
    """Convert a hex color string (e.g. '#1A73E8') to Google API rgbColor dict."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return {
        "red": int(h[0:2], 16) / 255.0,
        "green": int(h[2:4], 16) / 255.0,
        "blue": int(h[4:6], 16) / 255.0,
    }


def _build_text_style_request(
    object_id: str,
    style: Any,
) -> dict[str, Any]:
    """Build an updateTextStyle request for the Slides API from a TextStyle model."""
    from firefly_dworkers.design.models import TextStyle

    if not isinstance(style, TextStyle):
        return {}

    api_style: dict[str, Any] = {}
    fields: list[str] = []

    if style.font_name:
        api_style["fontFamily"] = style.font_name
        fields.append("fontFamily")
    if style.font_size:
        api_style["fontSize"] = {"magnitude": style.font_size, "unit": "PT"}
        fields.append("fontSize")
    if style.bold:
        api_style["bold"] = True
        fields.append("bold")
    if style.italic:
        api_style["italic"] = True
        fields.append("italic")
    if style.color:
        api_style["foregroundColor"] = {
            "opaqueColor": {"rgbColor": _hex_to_rgb(style.color)}
        }
        fields.append("foregroundColor")

    if not fields:
        return {}

    return {
        "updateTextStyle": {
            "objectId": object_id,
            "style": api_style,
            "fields": ",".join(fields),
            "textRange": {"type": "ALL"},
        }
    }


@tool_registry.register("google_slides", category="presentation")
class GoogleSlidesTool(PresentationTool):
    """Read, create, and modify Google Slides presentations via Slides API v1."""

    def __init__(
        self,
        *,
        service_account_key: str = "",
        credentials_json: str = "",
        scopes: Sequence[str] = ("https://www.googleapis.com/auth/presentations",),
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        super().__init__(
            "google_slides",
            description="Read, create, and modify Google Slides presentations.",
            timeout=timeout,
            guards=guards,
        )
        self._service_account_key = service_account_key
        self._credentials_json = credentials_json
        self._scopes = list(scopes)
        self._service: Any | None = None

    def _ensure_deps(self) -> None:
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "google-api-python-client and google-auth required. Install with: pip install firefly-dworkers[google]"
            )

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        self._ensure_deps()

        if self._service_account_key:
            creds = _sa.Credentials.from_service_account_file(self._service_account_key, scopes=self._scopes)
        elif self._credentials_json:
            import json

            info = json.loads(self._credentials_json)
            creds = _sa.Credentials.from_service_account_info(info, scopes=self._scopes)
        else:
            raise ConnectorAuthError("GoogleSlidesTool requires service_account_key or credentials_json")

        self._service = _build("slides", "v1", credentials=creds)
        return self._service

    # -- port implementation -------------------------------------------------

    async def _read_presentation(self, source: str) -> PresentationData:
        """Read a Google Slides presentation by ID."""
        svc = self._get_service()
        pres = await asyncio.to_thread(lambda: svc.presentations().get(presentationId=source).execute())

        slides = []
        for i, slide in enumerate(pres.get("slides", [])):
            title = ""
            content_parts: list[str] = []
            for element in slide.get("pageElements", []):
                shape = element.get("shape", {})
                text_elements = shape.get("text", {}).get("textElements", [])
                text = "".join(te.get("textRun", {}).get("content", "") for te in text_elements)
                ph = shape.get("placeholder", {})
                if ph.get("type") in ("TITLE", "CENTERED_TITLE"):
                    title = text.strip()
                elif text.strip():
                    content_parts.append(text.strip())

            slides.append(
                SlideData(
                    index=i,
                    layout=slide.get("slideProperties", {}).get("layoutObjectId", ""),
                    title=title,
                    content="\n".join(content_parts),
                )
            )

        layouts: list[str] = []
        for layout in pres.get("layouts", []):
            name = layout.get("layoutProperties", {}).get("displayName", "")
            if name:
                layouts.append(name)

        return PresentationData(
            slides=slides,
            master_layouts=layouts,
            slide_width=pres.get("pageSize", {}).get("width", {}).get("magnitude", 0),
            slide_height=pres.get("pageSize", {}).get("height", {}).get("magnitude", 0),
        )

    async def _create_presentation(self, template: str, slides: list[SlideSpec]) -> bytes:
        """Create a new Google Slides presentation. Returns presentation ID as bytes."""
        svc = self._get_service()

        body: dict[str, Any] = {"title": "Untitled Presentation"}
        if slides and slides[0].title:
            body["title"] = slides[0].title

        pres = await asyncio.to_thread(lambda: svc.presentations().create(body=body).execute())
        presentation_id = pres["presentationId"]

        # Add slides via batch update
        if slides:
            requests: list[dict[str, Any]] = []
            for _spec in slides:
                requests.append(
                    {
                        "createSlide": {
                            "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                        }
                    }
                )
            result = await asyncio.to_thread(
                lambda: (
                    svc.presentations()
                    .batchUpdate(
                        presentationId=presentation_id,
                        body={"requests": requests},
                    )
                    .execute()
                )
            )

            # Collect created slide IDs from the batch update reply
            slide_ids = []
            for reply in result.get("replies", []):
                create_reply = reply.get("createSlide", {})
                obj_id = create_reply.get("objectId", "")
                if obj_id:
                    slide_ids.append(obj_id)

            # Build styling / image / background requests
            style_requests = self._build_slide_enhancement_requests(slides, slide_ids, pres)
            if style_requests:
                await asyncio.to_thread(
                    lambda: (
                        svc.presentations()
                        .batchUpdate(
                            presentationId=presentation_id,
                            body={"requests": style_requests},
                        )
                        .execute()
                    )
                )

        return presentation_id.encode("utf-8")

    def _build_slide_enhancement_requests(
        self,
        slides: list[SlideSpec],
        slide_ids: list[str],
        pres_response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build batch update requests for styling, images, and backgrounds."""
        requests: list[dict[str, Any]] = []

        for i, spec in enumerate(slides):
            slide_id = slide_ids[i] if i < len(slide_ids) else None
            if not slide_id:
                continue

            # --- Background color ---
            if spec.background_color:
                rgb = _hex_to_rgb(spec.background_color)
                requests.append(
                    {
                        "updatePageProperties": {
                            "objectId": slide_id,
                            "pageProperties": {
                                "pageBackgroundFill": {
                                    "solidFill": {
                                        "color": {"rgbColor": rgb},
                                    }
                                }
                            },
                            "fields": "pageBackgroundFill.solidFill.color",
                        }
                    }
                )

            # --- Title styling ---
            if spec.title_style:
                # Use a deterministic element ID for the title placeholder
                title_element_id = f"{slide_id}_title"
                req = _build_text_style_request(title_element_id, spec.title_style)
                if req:
                    requests.append(req)

            # --- Body styling ---
            if spec.body_style:
                body_element_id = f"{slide_id}_body"
                req = _build_text_style_request(body_element_id, spec.body_style)
                if req:
                    requests.append(req)

            # --- Images ---
            for img in spec.images:
                url = img.image_ref or img.file_path
                if not url:
                    continue
                img_req: dict[str, Any] = {
                    "createImage": {
                        "url": url,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                        },
                    }
                }
                # Add size if provided
                size: dict[str, Any] = {}
                if img.width:
                    size["width"] = {"magnitude": img.width, "unit": "PT"}
                if img.height:
                    size["height"] = {"magnitude": img.height, "unit": "PT"}
                if size:
                    img_req["createImage"]["elementProperties"]["size"] = size
                # Add transform for position if provided
                if img.left or img.top:
                    img_req["createImage"]["elementProperties"]["transform"] = {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": img.left,
                        "translateY": img.top,
                        "unit": "PT",
                    }
                requests.append(img_req)

            # --- Charts ---
            # Limitation: Chart embedding in Google Slides requires rendering to
            # PNG, uploading to Google Drive, and using createImage with the
            # Drive URL.  This cross-service dependency (Slides → Drive) is not
            # supported by this adapter.  Use PowerPointTool for native chart
            # embedding, or pre-render charts and add them as images.

        return requests

    async def _modify_presentation(self, source: str, operations: list[SlideOperation]) -> bytes:
        """Modify a Google Slides presentation by ID."""
        svc = self._get_service()

        # Read current presentation state for update_content operations
        has_update = any(op.operation == "update_content" for op in operations)
        pres: dict[str, Any] = {}
        if has_update:
            pres = await asyncio.to_thread(
                lambda: svc.presentations().get(presentationId=source).execute()
            )

        requests: list[dict[str, Any]] = []
        for op in operations:
            if op.operation == "update_content":
                requests.extend(self._build_update_content_requests(pres, op))
            elif op.operation == "add_slide":
                requests.append(
                    {
                        "createSlide": {
                            "slideLayoutReference": {
                                "predefinedLayout": op.data.get("layout", "BLANK"),
                            },
                        }
                    }
                )

        if requests:
            await asyncio.to_thread(
                lambda: (
                    svc.presentations()
                    .batchUpdate(
                        presentationId=source,
                        body={"requests": requests},
                    )
                    .execute()
                )
            )

        return source.encode("utf-8")

    @staticmethod
    def _build_update_content_requests(
        pres: dict[str, Any],
        op: SlideOperation,
    ) -> list[dict[str, Any]]:
        """Build replaceAllText requests for an update_content operation.

        Supported ``op.data`` keys:

        * ``title`` — new text for the title placeholder
        * ``body`` — new text for the body/subtitle placeholder

        The method reads the presentation to find existing placeholder text on
        the target slide and builds ``replaceAllText`` requests that swap the
        old text for the new text.
        """
        slide_index = op.slide_index
        slides = pres.get("slides", [])
        if slide_index >= len(slides):
            return []

        slide = slides[slide_index]
        requests: list[dict[str, Any]] = []

        title_types = {"TITLE", "CENTERED_TITLE"}
        body_types = {"BODY", "SUBTITLE"}

        for element in slide.get("pageElements", []):
            shape = element.get("shape", {})
            ph = shape.get("placeholder", {})
            ph_type = ph.get("type", "")
            text_elements = shape.get("text", {}).get("textElements", [])
            old_text = "".join(
                te.get("textRun", {}).get("content", "") for te in text_elements
            ).strip()

            if not old_text:
                continue

            if ph_type in title_types and "title" in op.data:
                requests.append(
                    {
                        "replaceAllText": {
                            "containsText": {"text": old_text, "matchCase": True},
                            "replaceText": op.data["title"],
                            "pageObjectIds": [slide.get("objectId", "")],
                        }
                    }
                )
            elif ph_type in body_types and "body" in op.data:
                requests.append(
                    {
                        "replaceAllText": {
                            "containsText": {"text": old_text, "matchCase": True},
                            "replaceText": op.data["body"],
                            "pageObjectIds": [slide.get("objectId", "")],
                        }
                    }
                )

        return requests
