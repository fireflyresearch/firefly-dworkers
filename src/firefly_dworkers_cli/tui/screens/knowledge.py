"""Knowledge Base screen — search indexed documents and trigger indexing."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, ListItem, ListView, Static, TextArea


class SearchResult(ListItem):
    def __init__(self, source: str, content: str, chunk_id: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._source = source
        self._content = content
        self._chunk_id = chunk_id

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._source, classes="panel-title")
            preview = self._content[:200] + "..." if len(self._content) > 200 else self._content
            yield Static(preview, classes="text-dim")


class KnowledgeScreen(Vertical):
    DEFAULT_CSS = """
    KnowledgeScreen { height: 1fr; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static("\u2630 Knowledge Base", classes="panel-title")
        with Horizontal():
            yield Input(placeholder="Search knowledge base...", id="kb-search")
            yield Button("Search", id="kb-search-btn", variant="primary")
        yield ListView(id="kb-results")
        yield Static("Index New Content", classes="section-label")
        with Vertical(classes="stats-card"):
            yield Label("Source identifier:")
            yield Input(placeholder="e.g. report-q4-2025", id="index-source")
            yield Label("Content:")
            yield TextArea(id="index-content")
            yield Button("Index", id="index-btn", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "kb-search-btn":
            await self._do_search()
        elif event.button.id == "index-btn":
            await self._do_index()

    async def _do_search(self) -> None:
        query = self.query_one("#kb-search", Input).value
        if not query:
            return
        results_list = self.query_one("#kb-results", ListView)
        results_list.clear()
        try:
            from firefly_dworkers.knowledge.repository import KnowledgeRepository
            repo = KnowledgeRepository()
            results = repo.search(query, max_results=10)
            for chunk in results:
                results_list.append(SearchResult(source=chunk.source, content=chunk.content, chunk_id=chunk.chunk_id))
            if not results:
                results_list.append(ListItem(Label("No results found")))
        except Exception as e:
            results_list.append(ListItem(Label(f"Search error: {e}")))

    async def _do_index(self) -> None:
        source = self.query_one("#index-source", Input).value
        content = self.query_one("#index-content", TextArea).text
        if not source or not content:
            self.notify("Source and content are required", severity="warning")
            return
        try:
            import uuid

            from firefly_dworkers.knowledge.repository import DocumentChunk, KnowledgeRepository
            repo = KnowledgeRepository()
            chunk = DocumentChunk(chunk_id=f"chunk_{uuid.uuid4().hex[:8]}", source=source, content=content)
            repo.index(chunk)
            self.notify(f"Indexed: {source}", severity="information")
            self.query_one("#index-source", Input).value = ""
            self.query_one("#index-content", TextArea).clear()
        except Exception as e:
            self.notify(f"Index error: {e}", severity="error")
