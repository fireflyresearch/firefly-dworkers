"""Analytics screen — usage metrics, costs, and worker utilization."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Sparkline, Static

from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.backend.store import ConversationStore


class AnalyticsScreen(Vertical):
    DEFAULT_CSS = """
    AnalyticsScreen { height: 1fr; padding: 1 2; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._client: DworkersClient | None = None
        self._store = ConversationStore()

    def compose(self) -> ComposeResult:
        yield Static("\u2261 Analytics", classes="panel-title")
        with Horizontal(id="analytics-stats"):
            with Vertical(classes="stats-card"):
                yield Static("0", id="stat-tokens", classes="stat-value")
                yield Static("Total Tokens", classes="text-dim")
            with Vertical(classes="stats-card"):
                yield Static("$0.00", id="stat-cost", classes="stat-value")
                yield Static("Total Cost", classes="text-dim")
            with Vertical(classes="stats-card"):
                yield Static("0", id="stat-tasks", classes="stat-value")
                yield Static("Tasks Completed", classes="text-dim")
            with Vertical(classes="stats-card"):
                yield Static("0ms", id="stat-latency", classes="stat-value")
                yield Static("Avg Response", classes="text-dim")
        yield Static("Token Usage (last 30 days)", classes="section-label")
        yield Sparkline([0] * 30, id="usage-sparkline")
        yield Static("Cost by Model", classes="section-label")
        yield DataTable(id="cost-model-table")
        yield Static("Usage by Worker", classes="section-label")
        yield DataTable(id="usage-worker-table")

    async def on_mount(self) -> None:
        self._client = await create_client()
        model_table = self.query_one("#cost-model-table", DataTable)
        model_table.add_columns("Model", "Tokens", "Cost (USD)", "Calls")
        worker_table = self.query_one("#usage-worker-table", DataTable)
        worker_table.add_columns("Worker", "Tasks", "Tokens", "Avg Duration")
        await self._refresh()

    async def _refresh(self) -> None:
        if not self._client:
            return
        stats = await self._client.get_usage_stats()
        self.query_one("#stat-tokens", Static).update(f"{stats.total_tokens:,}")
        self.query_one("#stat-cost", Static).update(f"${stats.total_cost_usd:.2f}")
        self.query_one("#stat-tasks", Static).update(str(stats.tasks_completed))
        self.query_one("#stat-latency", Static).update(f"{stats.avg_response_ms:.0f}ms")
        model_table = self.query_one("#cost-model-table", DataTable)
        model_table.clear()
        for model, tokens in stats.by_model.items():
            model_table.add_row(model, str(tokens), "$0.00", "0")
        worker_table = self.query_one("#usage-worker-table", DataTable)
        worker_table.clear()
        for worker, tasks in stats.by_worker.items():
            worker_table.add_row(worker, str(tasks), "0", "0ms")
        convs = self._store.list_conversations()
        total_msgs = sum(c.message_count for c in convs)
        self.query_one("#stat-tasks", Static).update(str(total_msgs))
