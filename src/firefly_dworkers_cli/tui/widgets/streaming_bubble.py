"""Live-updating message bubble for streaming agent responses."""

from __future__ import annotations

from datetime import UTC, datetime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Markdown, Static

from firefly_dworkers_cli.tui.widgets.message_bubble import MessageBubble


class StreamingBubble(Static):
    """Message bubble that updates as tokens stream in."""

    def __init__(
        self,
        sender: str,
        role: str = "",
        **kwargs,
    ) -> None:
        super().__init__(classes="message-bubble message-bubble-agent", **kwargs)
        self._sender = sender
        self._role = role
        self._tokens: list[str] = []
        self._content_widget: Markdown | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                f"\u2726  {self._sender} [AI WORKER]  working...",
                classes="message-header",
                id="streaming-header",
            )
            self._content_widget = Markdown(
                "\u25CF\u25CF\u25CF Thinking...", classes="message-content"
            )
            yield self._content_widget

    def append_token(self, token: str) -> None:
        self._tokens.append(token)
        if self._content_widget is not None:
            self._content_widget.update("".join(self._tokens))

    def finalize(self) -> MessageBubble:
        """Convert to a static MessageBubble once streaming is done."""
        return MessageBubble(
            sender=self._sender,
            content="".join(self._tokens),
            timestamp=datetime.now(UTC),
            is_ai=True,
            role=self._role,
        )

    @property
    def full_content(self) -> str:
        return "".join(self._tokens)
