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
                "google-api-python-client and google-auth required. "
                "Install with: pip install firefly-dworkers[google]"
            )

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service
        self._ensure_deps()

        if self._service_account_key:
            creds = _sa.Credentials.from_service_account_file(
                self._service_account_key, scopes=self._scopes
            )
        elif self._credentials_json:
            import json

            info = json.loads(self._credentials_json)
            creds = _sa.Credentials.from_service_account_info(
                info, scopes=self._scopes
            )
        else:
            raise ConnectorAuthError(
                "GoogleSlidesTool requires service_account_key or credentials_json"
            )

        self._service = _build("slides", "v1", credentials=creds)
        return self._service

    # -- port implementation -------------------------------------------------

    async def _read_presentation(self, source: str) -> PresentationData:
        """Read a Google Slides presentation by ID."""
        svc = self._get_service()
        pres = await asyncio.to_thread(
            lambda: svc.presentations().get(presentationId=source).execute()
        )

        slides = []
        for i, slide in enumerate(pres.get("slides", [])):
            title = ""
            content_parts: list[str] = []
            for element in slide.get("pageElements", []):
                shape = element.get("shape", {})
                text_elements = shape.get("text", {}).get("textElements", [])
                text = "".join(
                    te.get("textRun", {}).get("content", "")
                    for te in text_elements
                )
                ph = shape.get("placeholder", {})
                if ph.get("type") in ("TITLE", "CENTERED_TITLE"):
                    title = text.strip()
                elif text.strip():
                    content_parts.append(text.strip())

            slides.append(
                SlideData(
                    index=i,
                    layout=slide.get("slideProperties", {}).get(
                        "layoutObjectId", ""
                    ),
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
            slide_width=pres.get("pageSize", {})
            .get("width", {})
            .get("magnitude", 0),
            slide_height=pres.get("pageSize", {})
            .get("height", {})
            .get("magnitude", 0),
        )

    async def _create_presentation(
        self, template: str, slides: list[SlideSpec]
    ) -> bytes:
        """Create a new Google Slides presentation. Returns presentation ID as bytes."""
        svc = self._get_service()

        body: dict[str, Any] = {"title": "Untitled Presentation"}
        if slides and slides[0].title:
            body["title"] = slides[0].title

        pres = await asyncio.to_thread(
            lambda: svc.presentations().create(body=body).execute()
        )
        presentation_id = pres["presentationId"]

        # Add slides via batch update
        if slides:
            requests: list[dict[str, Any]] = []
            for _spec in slides:
                requests.append(
                    {
                        "createSlide": {
                            "slideLayoutReference": {
                                "predefinedLayout": "TITLE_AND_BODY"
                            },
                        }
                    }
                )
            await asyncio.to_thread(
                lambda: svc.presentations()
                .batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": requests},
                )
                .execute()
            )

        return presentation_id.encode("utf-8")

    async def _modify_presentation(
        self, source: str, operations: list[SlideOperation]
    ) -> bytes:
        """Modify a Google Slides presentation by ID."""
        svc = self._get_service()

        requests: list[dict[str, Any]] = []
        for op in operations:
            if op.operation == "update_content" and "title" in op.data:
                # Would need slide object IDs; simplified version
                pass
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
                lambda: svc.presentations()
                .batchUpdate(
                    presentationId=source,
                    body={"requests": requests},
                )
                .execute()
            )

        return source.encode("utf-8")
