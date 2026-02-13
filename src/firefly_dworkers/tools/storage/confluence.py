"""ConfluenceTool — document access via Atlassian Confluence."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool


class ConfluenceTool(DocumentStorageTool):
    """Atlassian Confluence document access.

    Requires ``atlassian-python-api`` for production use.
    The current implementation provides placeholder responses that allow the
    full architecture to work end-to-end while credentials are configured.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        username: str = "",
        api_token: str = "",
        space_key: str = "",
        **kwargs: Any,
    ):
        super().__init__("confluence", description="Access Confluence pages and spaces")
        self._base_url = base_url
        self._username = username
        self._api_token = api_token
        self._space_key = space_key

    async def _search(self, query: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="confluence-placeholder",
                name=f"Search: {query}",
                path="",
                content=f"Confluence search for '{query}' (configure credentials to enable)",
            )
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        return DocumentResult(
            id=resource_id or "confluence-read",
            name=path or resource_id,
            content="Confluence read (configure credentials to enable)",
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="confluence-list",
                name=path or "/",
                content="Confluence listing (configure credentials to enable)",
            )
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        return DocumentResult(
            id="confluence-write",
            name=path,
            content=f"Written {len(content)} chars to Confluence (configure credentials to enable)",
        )
