"""Dashboard screen — overview with stats, activity feed, and worker status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, ListItem, ListView, Static

from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.backend.store import ConversationStore


class StatsCard(Vertical):
    """A single stat card with value and label."""

    DEFAULT_CSS = """
    StatsCard {
        background: #2A2A3E;
        border: round #313244;
        padding: 1 2;
        width: 1fr;
        height: 7;
        content-align: center middle;
    }
    """

    def __init__(self, value: str, label: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._value = value
        self._label = label

    def compose(self) -> ComposeResult:
        yield Static(self._value, classes="stat-value")
        yield Static(self._label, classes="text-dim")


class DashboardScreen(Vertical):
    """Overview dashboard with quick stats and activity."""

    DEFAULT_CSS = """
    DashboardScreen {
        height: 1fr;
        padding: 1 2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._store = ConversationStore()
        self._client: DworkersClient | None = None

    def compose(self) -> ComposeResult:
        yield Static("\u2302 Dashboard", classes="panel-title")
        with Horizontal(id="stats-row"):
            yield StatsCard(value="0", label="Active Conversations")
            yield StatsCard(value="0", label="Tasks Completed")
            yield StatsCard(value="$0.00", label="Total Cost")
            yield StatsCard(value="0", label="Workers Active")
        with Horizontal():
            with Vertical(classes="stats-card"):
                yield Static("Recent Activity", classes="panel-title")
                yield ListView(id="activity-feed")
            with Vertical(classes="stats-card"):
                yield Static("Worker Status", classes="panel-title")
                yield ListView(id="worker-status")

    async def on_mount(self) -> None:
        self._client = await create_client()
        await self._refresh()

    async def _refresh(self) -> None:
        convs = self._store.list_conversations()
        stats_row = self.query_one("#stats-row", Horizontal)
        cards = list(stats_row.query(StatsCard))
        if cards:
            cards[0]._value = str(len(convs))
            cards[0].refresh()
        feed = self.query_one("#activity-feed", ListView)
        feed.clear()
        for conv in convs[:10]:
            time_str = conv.updated_at.strftime("%b %d %H:%M")
            feed.append(ListItem(Label(f"{time_str} — {conv.title}")))
        if self._client:
            workers = await self._client.list_workers()
            status_list = self.query_one("#worker-status", ListView)
            status_list.clear()
            for w in workers:
                icon = "\u25CF" if w.enabled else "\u25CB"
                status_list.append(ListItem(Label(f"{icon} {w.name} — idle")))
            stats = await self._client.get_usage_stats()
            if len(cards) > 1:
                cards[1]._value = str(stats.tasks_completed)
                cards[1].refresh()
            if len(cards) > 2:
                cards[2]._value = f"${stats.total_cost_usd:.2f}"
                cards[2].refresh()
