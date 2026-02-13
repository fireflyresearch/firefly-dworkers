"""GoogleDriveTool — document access via Google Drive API.

This adapter uses the Google API Python client for Drive operations.
Install with::

    pip install firefly-dworkers[google]
"""

from __future__ import annotations

import asyncio
import io
import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError
from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool

logger = logging.getLogger(__name__)

try:
    from google.oauth2 import service_account as _sa
    from googleapiclient.discovery import build as _build
    from googleapiclient.http import MediaIoBaseUpload as _MediaUpload

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleDriveTool(DocumentStorageTool):
    """Google Drive document access via the Drive API v3.

    Configuration parameters:

    * ``service_account_key`` -- path to the service account JSON key file.
    * ``credentials_json`` -- inline JSON string of the service account key
      (alternative to ``service_account_key``).
    * ``folder_id`` -- default folder ID to scope operations.
    * ``scopes`` -- OAuth2 scopes for Drive access.
    * ``timeout`` -- HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        service_account_key: str = "",
        credentials_json: str = "",
        folder_id: str = "",
        scopes: Sequence[str] = ("https://www.googleapis.com/auth/drive",),
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__(
            "google_drive",
            description="Access Google Drive documents and folders via Drive API",
            guards=guards,
        )
        self._service_account_key = service_account_key
        self._credentials_json = credentials_json
        self._folder_id = folder_id
        self._scopes = list(scopes)
        self._timeout = timeout
        self._service: Any | None = None

    def _ensure_deps(self) -> None:
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "google-api-python-client and google-auth are required for GoogleDriveTool. "
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
                "GoogleDriveTool requires service_account_key or credentials_json"
            )

        self._service = _build("drive", "v3", credentials=creds)
        return self._service

    # -- port implementation -------------------------------------------------

    async def _search(self, query: str) -> list[DocumentResult]:
        svc = self._get_service()
        q = f"name contains '{query}' and trashed = false"
        if self._folder_id:
            q += f" and '{self._folder_id}' in parents"

        response = await asyncio.to_thread(
            lambda: svc.files()
            .list(
                q=q,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink, parents)",
                pageSize=50,
            )
            .execute()
        )
        return [
            DocumentResult(
                id=f.get("id", ""),
                name=f.get("name", ""),
                path="/".join(f.get("parents", [])),
                content_type=f.get("mimeType", ""),
                size_bytes=int(f.get("size", 0)),
                modified_at=f.get("modifiedTime", ""),
                url=f.get("webViewLink", ""),
            )
            for f in response.get("files", [])
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        svc = self._get_service()
        file_id = resource_id
        if not file_id and path:
            # Resolve by name search
            results = await self._search(path.split("/")[-1])
            if not results:
                raise ConnectorError(f"File not found: {path}")
            file_id = results[0].id

        if not file_id:
            raise ConnectorError("GoogleDrive read requires resource_id or path")

        meta = await asyncio.to_thread(
            lambda: svc.files()
            .get(fileId=file_id, fields="id, name, mimeType, size, modifiedTime, webViewLink")
            .execute()
        )

        # Download content for exportable types
        content = ""
        mime = meta.get("mimeType", "")
        if mime.startswith("application/vnd.google-apps."):
            export_mime = "text/plain"
            data = await asyncio.to_thread(
                lambda: svc.files()
                .export(fileId=file_id, mimeType=export_mime)
                .execute()
            )
            content = data.decode("utf-8") if isinstance(data, bytes) else str(data)
        else:
            data = await asyncio.to_thread(
                lambda: svc.files().get_media(fileId=file_id).execute()
            )
            content = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)

        return DocumentResult(
            id=meta.get("id", ""),
            name=meta.get("name", ""),
            content=content[:100_000],
            content_type=mime,
            size_bytes=int(meta.get("size", 0)),
            modified_at=meta.get("modifiedTime", ""),
            url=meta.get("webViewLink", ""),
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        svc = self._get_service()
        folder_id = path if path and path != "/" else self._folder_id
        q = "trashed = false"
        if folder_id:
            q += f" and '{folder_id}' in parents"

        response = await asyncio.to_thread(
            lambda: svc.files()
            .list(
                q=q,
                fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
                pageSize=100,
            )
            .execute()
        )
        return [
            DocumentResult(
                id=f.get("id", ""),
                name=f.get("name", ""),
                path=path,
                content_type=f.get("mimeType", ""),
                size_bytes=int(f.get("size", 0)),
                modified_at=f.get("modifiedTime", ""),
                url=f.get("webViewLink", ""),
            )
            for f in response.get("files", [])
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        svc = self._get_service()
        name = path.split("/")[-1] if "/" in path else path
        body: dict[str, Any] = {"name": name}
        if self._folder_id:
            body["parents"] = [self._folder_id]

        media = _MediaUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype="text/plain",
            resumable=False,
        )
        result = await asyncio.to_thread(
            lambda: svc.files().create(body=body, media_body=media, fields="id, name, webViewLink").execute()
        )
        return DocumentResult(
            id=result.get("id", ""),
            name=result.get("name", name),
            path=path,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            url=result.get("webViewLink", ""),
        )
