"""Scrollable container for chat messages."""

from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widgets import Static

from firefly_dworkers_cli.tui.widgets.message_bubble import MessageBubble
from firefly_dworkers_cli.tui.widgets.streaming_bubble import StreamingBubble


class MessageList(VerticalScroll):
    """Scrollable list of chat messages with auto-scroll."""

    DEFAULT_CSS = """
    MessageList {
        height: 1fr;
        padding: 1 0;
    }
    """

    def add_message(self, bubble: MessageBubble | StreamingBubble) -> None:
        self.mount(bubble)
        self.scroll_end(animate=False)

    def add_divider(self, text: str) -> None:
        self.mount(Static(f"\n{'─' * 20} {text} {'─' * 20}\n", classes="divider"))

    def replace_streaming(
        self, streaming: StreamingBubble, final: MessageBubble
    ) -> None:
        streaming.remove()
        self.mount(final)
        self.scroll_end(animate=False)
