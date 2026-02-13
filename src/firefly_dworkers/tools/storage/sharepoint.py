"""SharePointTool — document access via Microsoft SharePoint / Graph API.

This adapter uses ``msal`` for authentication and ``httpx`` for async HTTP
calls against the Microsoft Graph API.  Install with::

    pip install firefly-dworkers[sharepoint]
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
    import msal

    MSAL_AVAILABLE = True
except ImportError:
    msal = None  # type: ignore[assignment]
    MSAL_AVAILABLE = False

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@tool_registry.register("sharepoint", category="storage")
class SharePointTool(DocumentStorageTool):
    """SharePoint document access via Microsoft Graph API.

    Parameters are intentionally granular so that every aspect of the
    connection can be driven from tenant YAML / env vars:

    * ``tenant_id`` -- Azure AD tenant ID.
    * ``client_id`` / ``client_secret`` -- OAuth2 client credentials.
    * ``site_url`` -- SharePoint site URL (used to resolve the site ID).
    * ``drive_id`` -- Optional pre-resolved drive ID; skips site lookup.
    * ``timeout`` -- HTTP request timeout in seconds.
    * ``scopes`` -- OAuth2 scopes (defaults to Graph ``Sites.ReadWrite.All``).
    """

    def __init__(
        self,
        *,
        tenant_id: str = "",
        client_id: str = "",
        client_secret: str = "",
        site_url: str = "",
        drive_id: str = "",
        timeout: float = 30.0,
        scopes: Sequence[str] = ("https://graph.microsoft.com/.default",),
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__(
            "sharepoint",
            description="Access SharePoint documents and lists via Microsoft Graph API",
            guards=guards,
        )
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._site_url = site_url
        self._drive_id = drive_id
        self._timeout = timeout
        self._scopes = list(scopes)
        self._access_token: str | None = None

    # -- authentication ------------------------------------------------------

    def _ensure_deps(self) -> None:
        if not MSAL_AVAILABLE:
            raise ImportError(
                "msal is required for SharePointTool. Install with: pip install firefly-dworkers[sharepoint]"
            )
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required for SharePointTool. Install with: pip install httpx")

    async def _get_token(self) -> str:
        """Acquire an OAuth2 access token via MSAL client credentials flow."""
        self._ensure_deps()
        if self._access_token:
            return self._access_token

        if not self._tenant_id or not self._client_id or not self._client_secret:
            raise ConnectorAuthError("SharePoint requires tenant_id, client_id, and client_secret")

        authority = f"https://login.microsoftonline.com/{self._tenant_id}"
        app = msal.ConfidentialClientApplication(
            self._client_id,
            authority=authority,
            client_credential=self._client_secret,
        )
        result = await asyncio.to_thread(app.acquire_token_for_client, scopes=self._scopes)
        if "access_token" not in result:
            raise ConnectorAuthError(
                f"SharePoint auth failed: {result.get('error_description', result.get('error', 'unknown'))}"
            )
        self._access_token = result["access_token"]
        return self._access_token

    async def _graph_get(self, path: str) -> dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{_GRAPH_BASE}{path}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 401:
                self._access_token = None
                raise ConnectorAuthError("SharePoint token expired or invalid")
            resp.raise_for_status()
            return resp.json()

    async def _graph_put(
        self, path: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.put(
                f"{_GRAPH_BASE}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": content_type,
                },
                content=content,
            )
            resp.raise_for_status()
            return resp.json()

    async def _resolve_drive(self) -> str:
        if self._drive_id:
            return self._drive_id
        if not self._site_url:
            raise ConnectorError("SharePoint requires either site_url or drive_id")
        # Resolve site by URL and get default drive
        hostname = self._site_url.split("//")[-1].split("/")[0]
        site_path = "/".join(self._site_url.split("//")[-1].split("/")[1:])
        data = await self._graph_get(f"/sites/{hostname}:/{site_path}")
        site_id = data["id"]
        drive_data = await self._graph_get(f"/sites/{site_id}/drive")
        self._drive_id = drive_data["id"]
        return self._drive_id

    # -- port implementation -------------------------------------------------

    async def _search(self, query: str) -> list[DocumentResult]:
        self._ensure_deps()
        drive_id = await self._resolve_drive()
        data = await self._graph_get(f"/drives/{drive_id}/root/search(q='{query}')")
        results = []
        for item in data.get("value", []):
            results.append(
                DocumentResult(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    path=item.get("parentReference", {}).get("path", ""),
                    content_type=item.get("file", {}).get("mimeType", ""),
                    size_bytes=item.get("size", 0),
                    modified_at=item.get("lastModifiedDateTime", ""),
                    url=item.get("webUrl", ""),
                )
            )
        return results

    async def _read(self, resource_id: str, path: str) -> DocumentResult:
        self._ensure_deps()
        drive_id = await self._resolve_drive()
        if resource_id:
            item = await self._graph_get(f"/drives/{drive_id}/items/{resource_id}")
        elif path:
            item = await self._graph_get(f"/drives/{drive_id}/root:/{path.lstrip('/')}")
        else:
            raise ConnectorError("SharePoint read requires resource_id or path")

        # Download content for small files (< 4 MB)
        content = ""
        size = item.get("size", 0)
        if size < 4_194_304 and "file" in item:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                dl = await client.get(
                    item.get(
                        "@microsoft.graph.downloadUrl", f"{_GRAPH_BASE}/drives/{drive_id}/items/{item['id']}/content"
                    ),
                    headers={"Authorization": f"Bearer {token}"},
                )
                dl.raise_for_status()
                content = dl.text

        return DocumentResult(
            id=item.get("id", ""),
            name=item.get("name", ""),
            path=item.get("parentReference", {}).get("path", ""),
            content=content,
            content_type=item.get("file", {}).get("mimeType", ""),
            size_bytes=size,
            modified_at=item.get("lastModifiedDateTime", ""),
            url=item.get("webUrl", ""),
        )

    async def _list(self, path: str) -> list[DocumentResult]:
        self._ensure_deps()
        drive_id = await self._resolve_drive()
        if path and path != "/":
            data = await self._graph_get(f"/drives/{drive_id}/root:/{path.lstrip('/')}:/children")
        else:
            data = await self._graph_get(f"/drives/{drive_id}/root/children")

        return [
            DocumentResult(
                id=item.get("id", ""),
                name=item.get("name", ""),
                path=f"{path.rstrip('/')}/{item.get('name', '')}",
                content_type=item.get("file", {}).get("mimeType", "") if "file" in item else "folder",
                size_bytes=item.get("size", 0),
                modified_at=item.get("lastModifiedDateTime", ""),
                url=item.get("webUrl", ""),
            )
            for item in data.get("value", [])
        ]

    async def _write(self, path: str, content: str) -> DocumentResult:
        self._ensure_deps()
        drive_id = await self._resolve_drive()
        item = await self._graph_put(
            f"/drives/{drive_id}/root:/{path.lstrip('/')}:/content",
            content.encode("utf-8"),
            "text/plain",
        )
        return DocumentResult(
            id=item.get("id", ""),
            name=item.get("name", ""),
            path=path,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            modified_at=item.get("lastModifiedDateTime", ""),
            url=item.get("webUrl", ""),
        )
