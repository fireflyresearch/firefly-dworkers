"""ConfluenceTool — document access via Atlassian Confluence REST API.

This adapter uses the ``atlassian-python-api`` library.  Install with::

    pip install firefly-dworkers[confluence]
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError
from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.storage.base import DocumentResult, DocumentStorageTool

logger = logging.getLogger(__name__)

try:
    from atlassian import Confluence as _Confluence

    CONFLUENCE_AVAILABLE = True
except ImportError:
    CONFLUENCE_AVAILABLE = False


@tool_registry.register("confluence", category="storage")
class ConfluenceTool(DocumentStorageTool):
    """Atlassian Confluence document access via the REST API.

    Configuration parameters:

    * ``base_url`` -- Confluence base URL (e.g. ``https://wiki.example.com``).
    * ``username`` -- Confluence username (email for Cloud).
    * ``api_token`` -- API token (Cloud) or password (Server/DC).
    * ``space_key`` -- Default space key to scope operations.
    * ``cloud`` -- Whether this is a Cloud instance (affects API behaviour).
    * ``timeout`` -- HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        username: str = "",
        api_token: str = "",
        space_key: str = "",
        cloud: bool = True,
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__(
            "confluence",
            description="Access Confluence pages and spaces via REST API",
            guards=guards,
        )
        self._base_url = base_url
        self._username = username
        self._api_token = api_token
        self._space_key = space_key
        self._cloud = cloud
        self._timeout = timeout
        self._client: Any | None = None

    def _ensure_deps(self) -> None:
        if not CONFLUENCE_AVAILABLE:
            raise ImportError(
                "atlassian-python-api is required for ConfluenceTool. "
                "Install with: pip install firefly-dworkers[confluence]"
            )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._ensure_deps()

        if not self._base_url or not self._username or not self._api_token:
            raise ConnectorAuthError(
                "ConfluenceTool requires base_url, username, and api_token"
            )

        self._client = _Confluence(
            url=self._base_url,
            username=self._username,
            password=self._api_token,
            cloud=self._cloud,
            timeout=self._timeout,
        )
        return self._client

    # -- port implementation -------------------------------------------------

    async def _search(self, query: str) -> list[DocumentResult]:
        client = self._get_client()
        cql = f'text ~ "{query}"'
        if self._space_key:
            cql += f' AND space = "{self._space_key}"'

        results_data = await asyncio.to_thread(
            client.cql, cql, limit=50
        )
        pages = results_data.get("results", [])
        return [
            DocumentResult(
                id=str(page.get("content", {}).get("id", page.get("id", ""))),
                name=page.get("content", {}).get("title", page.get("title", "")),
                path=page.get("content", {}).get("_links", {}).get("webui", ""),
                url=f"{self._base_url}{page.get('content', {}).get('_links', {}).get('webui', '')}",
            )
            for page in pages
        ]

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        client = self._get_client()
        if not resource_id:
            raise ConnectorError("Confluence read requires resource_id (page ID)")

        page = await asyncio.to_thread(
            client.get_page_by_id,
            resource_id,
            expand="body.storage,version",
        )

        body_html = page.get("body", {}).get("storage", {}).get("value", "")

        return DocumentResult(
            id=str(page.get("id", "")),
            name=page.get("title", ""),
            path=page.get("_links", {}).get("webui", ""),
            content=body_html,
            content_type="text/html",
            modified_at=page.get("version", {}).get("when", ""),
            url=f"{self._base_url}{page.get('_links', {}).get('webui', '')}",
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        client = self._get_client()
        space = path if path and path != "/" else self._space_key
        if not space:
            raise ConnectorError("Confluence list requires a space_key or path")

        pages = await asyncio.to_thread(
            client.get_all_pages_from_space,
            space,
            start=0,
            limit=100,
            expand="version",
        )
        return [
            DocumentResult(
                id=str(page.get("id", "")),
                name=page.get("title", ""),
                path=page.get("_links", {}).get("webui", ""),
                modified_at=page.get("version", {}).get("when", ""),
                url=f"{self._base_url}{page.get('_links', {}).get('webui', '')}",
            )
            for page in pages
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        client = self._get_client()
        space = self._space_key
        if not space:
            raise ConnectorError("Confluence write requires space_key")

        title = path.split("/")[-1] if "/" in path else path
        result = await asyncio.to_thread(
            client.create_page,
            space,
            title,
            content,
            parent_id=None,
            type="page",
            representation="storage",
        )
        return DocumentResult(
            id=str(result.get("id", "")),
            name=result.get("title", title),
            path=result.get("_links", {}).get("webui", ""),
            content=content,
            size_bytes=len(content.encode("utf-8")),
            url=f"{self._base_url}{result.get('_links', {}).get('webui', '')}",
        )
