"""SlackTool — send and receive messages via Slack Web API.

Uses the ``slack-sdk`` library.  Install with::

    pip install firefly-dworkers[slack]
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
    from slack_sdk import WebClient as _SlackClient
    from slack_sdk.errors import SlackApiError as _SlackApiError

    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False


@tool_registry.register("slack", category="communication")
class SlackTool(MessageTool):
    """Slack communication via the Web API.

    Configuration parameters:

    * ``bot_token`` -- Slack Bot User OAuth Token (``xoxb-...``).
    * ``app_token`` -- Optional App-Level Token for Socket Mode.
    * ``default_channel`` -- Default channel to post to.
    * ``timeout`` -- HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        bot_token: str = "",
        app_token: str = "",
        default_channel: str = "",
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__("slack", description="Send and receive messages via Slack", guards=guards)
        self._bot_token = bot_token
        self._app_token = app_token
        self._default_channel = default_channel
        self._timeout = timeout
        self._client: Any | None = None

    def _ensure_deps(self) -> None:
        if not SLACK_AVAILABLE:
            raise ImportError(
                "slack-sdk is required for SlackTool. "
                "Install with: pip install firefly-dworkers[slack]"
            )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._ensure_deps()
        if not self._bot_token:
            raise ConnectorAuthError("SlackTool requires bot_token")

        self._client = _SlackClient(token=self._bot_token, timeout=self._timeout)
        return self._client

    # -- port implementation -------------------------------------------------

    async def _send(self, channel: str, content: str) -> Message:
        client = self._get_client()
        target = channel or self._default_channel
        if not target:
            raise ConnectorError("SlackTool send requires a channel")

        try:
            resp = await asyncio.to_thread(
                client.chat_postMessage, channel=target, text=content
            )
        except _SlackApiError as exc:
            raise ConnectorError(f"Slack send failed: {exc.response['error']}") from exc

        return Message(
            id=resp.get("ts", ""),
            channel=target,
            sender="bot",
            content=content,
            timestamp=resp.get("ts", ""),
        )

    async def _read(self, channel: str, message_id: str) -> list[Message]:
        client = self._get_client()
        target = channel or self._default_channel
        if not target:
            raise ConnectorError("SlackTool read requires a channel")

        try:
            if message_id:
                # Get replies to a specific thread
                resp = await asyncio.to_thread(
                    client.conversations_replies,
                    channel=target,
                    ts=message_id,
                    limit=50,
                )
            else:
                resp = await asyncio.to_thread(
                    client.conversations_history,
                    channel=target,
                    limit=20,
                )
        except _SlackApiError as exc:
            raise ConnectorError(f"Slack read failed: {exc.response['error']}") from exc

        return [
            Message(
                id=msg.get("ts", ""),
                channel=target,
                sender=msg.get("user", msg.get("bot_id", "")),
                content=msg.get("text", ""),
                timestamp=msg.get("ts", ""),
            )
            for msg in resp.get("messages", [])
        ]

    async def _list_channels(self) -> list[str]:
        client = self._get_client()
        try:
            resp = await asyncio.to_thread(
                client.conversations_list,
                types="public_channel,private_channel",
                limit=200,
            )
        except _SlackApiError as exc:
            raise ConnectorError(f"Slack list_channels failed: {exc.response['error']}") from exc

        return [ch.get("name", "") for ch in resp.get("channels", [])]
