"""Conversations screen — searchable list of all conversations."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from firefly_dworkers_cli.tui.backend.models import ConversationSummary
from firefly_dworkers_cli.tui.backend.store import ConversationStore
from firefly_dworkers_cli.tui.widgets.status_badge import StatusBadge


class OpenConversation(Message):
    """Posted when the user selects or creates a conversation."""

    def __init__(self, conversation_id: str) -> None:
        super().__init__()
        self.conversation_id = conversation_id


class ConversationItem(ListItem):
    """A single conversation entry showing title, status, participants, and metadata."""

    DEFAULT_CSS = """
    ConversationItem {
        height: auto;
        padding: 1 2;
    }

    ConversationItem .conv-title {
        text-style: bold;
        width: 1fr;
    }

    ConversationItem .conv-meta {
        color: #6C7086;
        width: 1fr;
    }

    ConversationItem .conv-header {
        height: 1;
        width: 1fr;
    }
    """

    def __init__(self, summary: ConversationSummary, **kwargs) -> None:
        super().__init__(**kwargs)
        self._summary = summary

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(classes="conv-header"):
                yield Static(self._summary.title, classes="conv-title")
                variant = "success" if self._summary.status == "active" else "default"
                yield StatusBadge(self._summary.status, variant=variant)

            participants = ", ".join(self._summary.participants) or "no participants"
            updated = self._summary.updated_at.strftime("%b %d, %H:%M")
            tags = " ".join(f"[{t}]" for t in self._summary.tags) if self._summary.tags else ""
            meta_parts = [
                f"{self._summary.message_count} msgs",
                participants,
                updated,
            ]
            if tags:
                meta_parts.append(tags)
            yield Static(" | ".join(meta_parts), classes="conv-meta")


class ConversationsScreen(Vertical):
    """Searchable list of conversations with new-conversation button."""

    DEFAULT_CSS = """
    ConversationsScreen {
        height: 1fr;
        width: 1fr;
    }

    ConversationsScreen .toolbar {
        height: 3;
        background: #181825;
        border-bottom: solid #313244;
        padding: 0 2;
        align: left middle;
    }

    ConversationsScreen .toolbar-title {
        width: 1fr;
        text-style: bold;
    }

    ConversationsScreen .search-bar {
        height: auto;
        padding: 1 2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._store = ConversationStore()
        self._conversations: list[ConversationSummary] = []

    def compose(self) -> ComposeResult:
        with Horizontal(classes="toolbar"):
            yield Label("Conversations", classes="toolbar-title")
            yield Button("+ New", id="new-conv-btn", variant="primary")
        yield Input(
            placeholder="Search conversations...",
            id="conv-search",
            classes="search-bar",
        )
        yield ListView(id="conv-list")

    def on_mount(self) -> None:
        self._refresh_list()

    def _refresh_list(self, filter_text: str = "") -> None:
        """Load conversations from store, filter, and populate the list view."""
        self._conversations = self._store.list_conversations()

        filtered = self._conversations
        if filter_text:
            lower_filter = filter_text.lower()
            filtered = [
                c
                for c in self._conversations
                if lower_filter in c.title.lower()
                or any(lower_filter in t.lower() for t in c.tags)
                or any(lower_filter in p.lower() for p in c.participants)
            ]

        list_view = self.query_one("#conv-list", ListView)
        list_view.clear()
        for summary in filtered:
            list_view.append(ConversationItem(summary, id=f"conv-{summary.id}"))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter conversations as the user types in the search bar."""
        if event.input.id == "conv-search":
            self._refresh_list(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Open the selected conversation."""
        item = event.item
        if isinstance(item, ConversationItem):
            self.post_message(OpenConversation(item._summary.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle the New button — open a blank conversation."""
        if event.button.id == "new-conv-btn":
            self.post_message(OpenConversation(""))
