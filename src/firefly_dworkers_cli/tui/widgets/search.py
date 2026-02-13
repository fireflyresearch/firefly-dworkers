"""Command palette / search modal (Ctrl+K)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

COMMANDS = [
    ("goto:dashboard", "Go to Dashboard"),
    ("goto:conversations", "Go to Conversations"),
    ("goto:deliverables", "Go to Deliverables"),
    ("goto:analytics", "Go to Analytics"),
    ("goto:templates-reports", "Go to Reports"),
    ("goto:templates-decks", "Go to Decks"),
    ("goto:templates-memos", "Go to Memos"),
    ("goto:team", "Go to Team"),
    ("goto:knowledge", "Go to Knowledge Base"),
    ("goto:integrations", "Go to Integrations"),
    ("goto:settings", "Go to Settings"),
    ("action:new-conversation", "New Conversation"),
    ("action:quit", "Quit"),
]


class CommandItem(ListItem):
    def __init__(self, command_id: str, label: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.command_id = command_id
        self._label = label

    def compose(self) -> ComposeResult:
        yield Label(self._label)


class SearchModal(ModalScreen):
    """Fuzzy search command palette."""

    DEFAULT_CSS = """
    SearchModal {
        align: center top;
        padding-top: 5;
    }

    #search-container {
        width: 60;
        height: auto;
        max-height: 25;
        background: #2A2A3E;
        border: round #6C5CE7;
        padding: 1;
    }
    """

    BINDINGS = [("escape", "dismiss_modal", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="search-container"):
            yield Input(placeholder="Type a command...", id="search-input")
            yield ListView(id="search-results")

    def on_mount(self) -> None:
        self._populate_results("")
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._populate_results(event.value)

    def _populate_results(self, query: str) -> None:
        results = self.query_one("#search-results", ListView)
        results.clear()
        q = query.lower()
        for cmd_id, label in COMMANDS:
            if not q or q in label.lower() or q in cmd_id.lower():
                results.append(CommandItem(command_id=cmd_id, label=label))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, CommandItem):
            self.dismiss(event.item.command_id)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
