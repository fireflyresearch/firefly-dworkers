"""GoogleDriveTool — document access via Google Drive."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool


class GoogleDriveTool(DocumentStorageTool):
    """Google Drive document access.

    Requires ``google-api-python-client`` and ``google-auth`` for production use.
    The current implementation provides placeholder responses that allow the
    full architecture to work end-to-end while credentials are configured.
    """

    def __init__(
        self,
        *,
        credentials_path: str = "",
        folder_id: str = "",
        **kwargs: Any,
    ):
        super().__init__("google_drive", description="Access Google Drive documents and folders")
        self._credentials_path = credentials_path
        self._folder_id = folder_id

    async def _search(self, query: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="gdrive-placeholder",
                name=f"Search: {query}",
                path="",
                content=f"Google Drive search for '{query}' (configure credentials to enable)",
            )
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        return DocumentResult(
            id=resource_id or "gdrive-read",
            name=path or resource_id,
            content="Google Drive read (configure credentials to enable)",
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="gdrive-list",
                name=path or "/",
                content="Google Drive listing (configure credentials to enable)",
            )
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        return DocumentResult(
            id="gdrive-write",
            name=path,
            content=f"Written {len(content)} chars to Google Drive (configure credentials to enable)",
        )
