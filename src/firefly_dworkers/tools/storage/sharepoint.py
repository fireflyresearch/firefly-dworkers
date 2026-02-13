"""SharePointTool — document access via Microsoft SharePoint."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool


class SharePointTool(DocumentStorageTool):
    """SharePoint document access.

    Requires ``msal`` and ``office365-rest-python-client`` for production use.
    The current implementation provides placeholder responses that allow the
    full architecture to work end-to-end while credentials are configured.
    """

    def __init__(
        self,
        *,
        tenant_id: str = "",
        site_url: str = "",
        credential_ref: str = "",
        **kwargs: Any,
    ):
        super().__init__("sharepoint", description="Access SharePoint documents and lists")
        self._tenant_id = tenant_id
        self._site_url = site_url
        self._credential_ref = credential_ref

    async def _search(self, query: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="sp-placeholder",
                name=f"Search: {query}",
                path="",
                content=f"SharePoint search for '{query}' (configure credentials to enable)",
            )
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        return DocumentResult(
            id=resource_id or "sp-read",
            name=path or resource_id,
            content="SharePoint read (configure credentials to enable)",
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        return [
            DocumentResult(
                id="sp-list",
                name=path or "/",
                content="SharePoint listing (configure credentials to enable)",
            )
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        return DocumentResult(
            id="sp-write",
            name=path,
            content=f"Written {len(content)} chars to SharePoint (configure credentials to enable)",
        )
