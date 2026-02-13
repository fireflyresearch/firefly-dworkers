"""TeamsTool — send and receive messages via Microsoft Teams / Graph API.

Uses ``httpx`` for async HTTP calls against the Microsoft Graph API and
``msal`` for OAuth2 authentication.  Install with::

    pip install firefly-dworkers[teams]
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError
from firefly_dworkers.tools.communication.base import Message, MessageTool
from firefly_dworkers.tools.registry import tool_registry

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


@tool_registry.register("teams", category="communication")
class TeamsTool(MessageTool):
    """Microsoft Teams communication via the Graph API.

    Configuration parameters:

    * ``tenant_id`` -- Azure AD tenant ID.
    * ``client_id`` / ``client_secret`` -- OAuth2 client credentials.
    * ``team_id`` -- Default team ID.
    * ``timeout`` -- HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        tenant_id: str = "",
        client_id: str = "",
        client_secret: str = "",
        team_id: str = "",
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__(
            "teams",
            description="Send and receive messages via Microsoft Teams",
            guards=guards,
        )
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._team_id = team_id
        self._timeout = timeout
        self._access_token: str | None = None

    def _ensure_deps(self) -> None:
        if not MSAL_AVAILABLE:
            raise ImportError(
                "msal is required for TeamsTool. Install with: pip install msal"
            )
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for TeamsTool. Install with: pip install httpx"
            )

    async def _get_token(self) -> str:
        self._ensure_deps()
        if self._access_token:
            return self._access_token

        if not self._tenant_id or not self._client_id or not self._client_secret:
            raise ConnectorAuthError(
                "TeamsTool requires tenant_id, client_id, and client_secret"
            )

        authority = f"https://login.microsoftonline.com/{self._tenant_id}"
        app = msal.ConfidentialClientApplication(
            self._client_id,
            authority=authority,
            client_credential=self._client_secret,
        )
        result = await asyncio.to_thread(
            app.acquire_token_for_client,
            scopes=["https://graph.microsoft.com/.default"],
        )
        if "access_token" not in result:
            raise ConnectorAuthError(
                f"Teams auth failed: {result.get('error_description', result.get('error', 'unknown'))}"
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
                raise ConnectorAuthError("Teams token expired or invalid")
            resp.raise_for_status()
            return resp.json()

    async def _graph_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{_GRAPH_BASE}{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    # -- port implementation -------------------------------------------------

    async def _send(self, channel: str, content: str) -> Message:
        self._ensure_deps()
        if not self._team_id:
            raise ConnectorError("TeamsTool requires team_id")
        channel_id = channel
        if not channel_id:
            raise ConnectorError("TeamsTool send requires a channel ID")

        body = {
            "body": {"contentType": "text", "content": content}
        }
        result = await self._graph_post(
            f"/teams/{self._team_id}/channels/{channel_id}/messages",
            body,
        )
        return Message(
            id=result.get("id", ""),
            channel=channel_id,
            sender=result.get("from", {}).get("user", {}).get("displayName", "bot"),
            content=content,
            timestamp=result.get("createdDateTime", ""),
        )

    async def _read(self, channel: str, message_id: str) -> list[Message]:
        self._ensure_deps()
        if not self._team_id:
            raise ConnectorError("TeamsTool requires team_id")
        channel_id = channel
        if not channel_id:
            raise ConnectorError("TeamsTool read requires a channel ID")

        if message_id:
            data = await self._graph_get(
                f"/teams/{self._team_id}/channels/{channel_id}/messages/{message_id}"
            )
            msgs = [data]
        else:
            data = await self._graph_get(
                f"/teams/{self._team_id}/channels/{channel_id}/messages"
            )
            msgs = data.get("value", [])

        return [
            Message(
                id=msg.get("id", ""),
                channel=channel_id,
                sender=msg.get("from", {}).get("user", {}).get("displayName", ""),
                content=msg.get("body", {}).get("content", ""),
                timestamp=msg.get("createdDateTime", ""),
            )
            for msg in msgs
        ]

    async def _list_channels(self) -> list[str]:
        self._ensure_deps()
        if not self._team_id:
            raise ConnectorError("TeamsTool requires team_id")

        data = await self._graph_get(f"/teams/{self._team_id}/channels")
        return [ch.get("displayName", "") for ch in data.get("value", [])]
