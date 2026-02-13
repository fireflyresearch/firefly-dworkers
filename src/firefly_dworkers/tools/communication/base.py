"""MessageTool — abstract base for messaging/communication providers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec
from pydantic import BaseModel


class Message(BaseModel):
    """Represents a message from a communication provider."""

    id: str
    channel: str = ""
    sender: str = ""
    content: str = ""
    timestamp: str = ""


class MessageTool(BaseTool):
    """Abstract base for messaging/communication tools.

    Subclasses must implement :meth:`_send`, :meth:`_read`, and
    :meth:`_list_channels` to provide access to a specific communication
    platform (e.g. Slack, Microsoft Teams, email).
    """

    def __init__(self, name: str, *, description: str = "", guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            name,
            description=description or f"Send and receive messages via {name}",
            tags=["communication", "messaging", name],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="action",
                    type_annotation="str",
                    description="One of: send, read, list_channels",
                    required=True,
                ),
                ParameterSpec(
                    name="channel",
                    type_annotation="str",
                    description="Channel/recipient",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="content",
                    type_annotation="str",
                    description="Message content (for send)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="message_id",
                    type_annotation="str",
                    description="Message ID (for read)",
                    required=False,
                    default="",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        if action == "send":
            result = await self._send(kwargs.get("channel", ""), kwargs.get("content", ""))
            return result.model_dump()
        if action == "read":
            results = await self._read(kwargs.get("channel", ""), kwargs.get("message_id", ""))
            return [m.model_dump() for m in results]
        if action == "list_channels":
            return await self._list_channels()
        raise ValueError(f"Unknown action '{action}'")

    @abstractmethod
    async def _send(self, channel: str, content: str) -> Message: ...

    @abstractmethod
    async def _read(self, channel: str, message_id: str) -> list[Message]: ...

    @abstractmethod
    async def _list_channels(self) -> list[str]: ...
