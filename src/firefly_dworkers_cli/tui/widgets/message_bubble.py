"""Chat message bubble with avatar, name, timestamp, and rich content."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Markdown, Static


class MessageBubble(Static):
    """A single chat message from a user or AI worker."""

    def __init__(
        self,
        sender: str,
        content: str,
        timestamp: datetime,
        *,
        is_ai: bool = False,
        role: str = "",
        status: str = "complete",
        **kwargs,
    ) -> None:
        css_class = "message-bubble-agent" if is_ai else "message-bubble-user"
        super().__init__(classes=f"message-bubble {css_class}", **kwargs)
        self._sender = sender
        self._content = content
        self._timestamp = timestamp
        self._is_ai = is_ai
        self._role = role
        self._status = status

    def compose(self) -> ComposeResult:
        time_str = self._timestamp.strftime("%H:%M")
        badge = " [AI WORKER]" if self._is_ai else ""
        icon = "\u2726" if self._is_ai else "\u25CF"

        with Vertical():
            yield Static(
                f"{icon}  {self._sender}{badge}  {time_str}",
                classes="message-header",
            )
            yield Markdown(self._content, classes="message-content")
