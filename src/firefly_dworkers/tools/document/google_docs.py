"""Google Docs adapter for DocumentTool.

This adapter uses the Google Docs API v1 for document operations.
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
from firefly_dworkers.tools.document.base import DocumentTool
from firefly_dworkers.tools.document.models import (
    DocumentData,
    DocumentOperation,
    ParagraphData,
    SectionSpec,
)
from firefly_dworkers.tools.registry import tool_registry

logger = logging.getLogger(__name__)

try:
    from google.oauth2 import service_account as _sa
    from googleapiclient.discovery import build as _build

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


@tool_registry.register("google_docs", category="document")
class GoogleDocsTool(DocumentTool):
    """Read, create, and modify Google Docs via Docs API v1."""

    def __init__(
        self,
        *,
        service_account_key: str = "",
        credentials_json: str = "",
        scopes: Sequence[str] = ("https://www.googleapis.com/auth/documents",),
        timeout: float = 60.0,
        guards: Sequence[GuardProtocol] = (),
    ) -> None:
        super().__init__(
            "google_docs",
            description="Read, create, and modify Google Docs.",
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
            raise ConnectorAuthError("GoogleDocsTool requires service_account_key or credentials_json")

        self._service = _build("docs", "v1", credentials=creds)
        return self._service

    # -- port implementation -------------------------------------------------

    async def _read_document(self, source: str) -> DocumentData:
        """Read a Google Doc by document ID."""
        svc = self._get_service()
        doc = await asyncio.to_thread(lambda: svc.documents().get(documentId=source).execute())

        title = doc.get("title", "")
        paragraphs = []
        for element in doc.get("body", {}).get("content", []):
            para = element.get("paragraph", {})
            if not para:
                continue
            text_parts = []
            for pe in para.get("elements", []):
                text_run = pe.get("textRun", {})
                content = text_run.get("content", "")
                if content:
                    text_parts.append(content)

            text = "".join(text_parts).rstrip("\n")
            if not text:
                continue

            style = para.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
            is_heading = style.startswith("HEADING")
            heading_level = 0
            if is_heading:
                try:
                    heading_level = int(style.replace("HEADING_", ""))
                except ValueError:
                    heading_level = 1

            paragraphs.append(
                ParagraphData(
                    text=text,
                    style=style,
                    is_heading=is_heading,
                    heading_level=heading_level,
                )
            )

        return DocumentData(
            title=title,
            paragraphs=paragraphs,
        )

    async def _create_document(self, title: str, sections: list[SectionSpec]) -> bytes:
        """Create a new Google Doc. Returns document ID as bytes."""
        svc = self._get_service()

        body: dict[str, Any] = {"title": title or "Untitled Document"}
        doc = await asyncio.to_thread(lambda: svc.documents().create(body=body).execute())
        document_id = doc["documentId"]

        # Build batch update requests for content
        if sections:
            requests = []
            index = 1  # Start after the implicit empty paragraph

            for section in sections:
                if section.heading:
                    requests.append(
                        {
                            "insertText": {
                                "location": {"index": index},
                                "text": section.heading + "\n",
                            }
                        }
                    )
                    requests.append(
                        {
                            "updateParagraphStyle": {
                                "range": {
                                    "startIndex": index,
                                    "endIndex": index + len(section.heading) + 1,
                                },
                                "paragraphStyle": {"namedStyleType": f"HEADING_{section.heading_level}"},
                                "fields": "namedStyleType",
                            }
                        }
                    )
                    index += len(section.heading) + 1

                if section.content:
                    requests.append(
                        {
                            "insertText": {
                                "location": {"index": index},
                                "text": section.content + "\n",
                            }
                        }
                    )
                    index += len(section.content) + 1

                for point in section.bullet_points:
                    requests.append(
                        {
                            "insertText": {
                                "location": {"index": index},
                                "text": point + "\n",
                            }
                        }
                    )
                    index += len(point) + 1

            if requests:
                await asyncio.to_thread(
                    lambda: (
                        svc.documents()
                        .batchUpdate(
                            documentId=document_id,
                            body={"requests": requests},
                        )
                        .execute()
                    )
                )

        return document_id.encode("utf-8")

    async def _modify_document(self, source: str, operations: list[DocumentOperation]) -> bytes:
        """Modify a Google Doc by document ID."""
        svc = self._get_service()

        requests = []
        for op in operations:
            if op.operation == "add_section":
                text = ""
                if op.data.get("heading"):
                    text += op.data["heading"] + "\n"
                if op.data.get("content"):
                    text += op.data["content"] + "\n"
                if text:
                    requests.append(
                        {
                            "insertText": {
                                "endOfSegmentLocation": {},
                                "text": text,
                            }
                        }
                    )

        if requests:
            await asyncio.to_thread(
                lambda: (
                    svc.documents()
                    .batchUpdate(
                        documentId=source,
                        body={"requests": requests},
                    )
                    .execute()
                )
            )

        return source.encode("utf-8")
