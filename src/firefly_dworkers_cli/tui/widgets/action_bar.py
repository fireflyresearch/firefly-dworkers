"""Inline action buttons below agent messages."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button


class ActionBar(Horizontal):
    """Row of action buttons (View Report, See Data, Export, etc.)."""

    DEFAULT_CSS = """
    ActionBar {
        height: 3;
        padding: 0 2;
    }

    ActionBar Button {
        margin-right: 1;
        min-width: 14;
    }
    """

    class ActionClicked(Message):
        def __init__(self, action: str, metadata: dict) -> None:
            super().__init__()
            self.action = action
            self.metadata = metadata

    def __init__(
        self,
        actions: list[tuple[str, str]],
        metadata: dict | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._actions = actions
        self._metadata = metadata or {}

    def compose(self) -> ComposeResult:
        for action_id, label in self._actions:
            yield Button(label, id=f"action-{action_id}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action_id = event.button.id.replace("action-", "") if event.button.id else ""
        self.post_message(self.ActionClicked(action_id, self._metadata))
