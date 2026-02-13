"""Chat input bar with slash commands and @mentions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, TextArea


class InputBar(Horizontal):
    """Input area for composing chat messages."""

    DEFAULT_CSS = """
    InputBar {
        dock: bottom;
        height: auto;
        max-height: 8;
        min-height: 3;
        background: #181825;
        border-top: solid #313244;
        padding: 1 2;
    }

    InputBar TextArea {
        width: 1fr;
        min-height: 1;
        max-height: 6;
    }

    InputBar Button {
        width: 10;
        margin-left: 1;
    }
    """

    class Submitted(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def compose(self) -> ComposeResult:
        yield TextArea(id="chat-input")
        yield Button("\u27A4 Send", id="send-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            self._submit()

    def _submit(self) -> None:
        text_area = self.query_one("#chat-input", TextArea)
        text = text_area.text.strip()
        if text:
            self.post_message(self.Submitted(text))
            text_area.clear()

    def focus_input(self) -> None:
        self.query_one("#chat-input", TextArea).focus()
