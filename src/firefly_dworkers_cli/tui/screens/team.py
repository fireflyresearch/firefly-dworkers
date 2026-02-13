"""Team screen — view and manage registered workers."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.backend.models import WorkerInfo
from firefly_dworkers_cli.tui.widgets.status_badge import StatusBadge


class WorkerDetailPanel(Vertical):
    """Detail view for a selected worker."""

    DEFAULT_CSS = """
    WorkerDetailPanel {
        height: auto;
        background: #2A2A3E;
        border: round #313244;
        padding: 1 2;
        margin: 1 0;
    }
    """

    def __init__(self, worker: WorkerInfo | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._worker = worker

    def compose(self) -> ComposeResult:
        if not self._worker:
            yield Static("Select a worker to view details", classes="text-dim")
            return
        yield Static(f"\u263B {self._worker.name}", classes="panel-title")
        yield Static(f"Role: {self._worker.role}")
        yield Static(f"Model: {self._worker.model or 'default'}")
        yield Static(f"Autonomy: {self._worker.autonomy}")
        enabled_text = "Enabled" if self._worker.enabled else "Disabled"
        variant = "success" if self._worker.enabled else "error"
        yield StatusBadge(enabled_text, variant=variant)
        if self._worker.tools:
            yield Static(f"Tools: {', '.join(self._worker.tools)}")

    def update_worker(self, worker: WorkerInfo) -> None:
        self._worker = worker
        self.remove_children()
        self.mount_all(list(self.compose()))


class TeamScreen(Vertical):
    """Worker management — list, inspect, toggle workers."""

    DEFAULT_CSS = """
    TeamScreen {
        height: 1fr;
        padding: 1 2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._client: DworkersClient | None = None
        self._workers: list[WorkerInfo] = []

    def compose(self) -> ComposeResult:
        yield Static("\u263B Team — Digital Workers", classes="panel-title")
        yield DataTable(id="worker-table")
        yield WorkerDetailPanel(id="worker-detail")

    async def on_mount(self) -> None:
        self._client = await create_client()
        table = self.query_one("#worker-table", DataTable)
        table.add_columns("Role", "Name", "Autonomy", "Model", "Status")
        await self._refresh_workers()

    async def _refresh_workers(self) -> None:
        if not self._client:
            return
        self._workers = await self._client.list_workers()
        table = self.query_one("#worker-table", DataTable)
        table.clear()
        for w in self._workers:
            status = "\u2713 Enabled" if w.enabled else "\u2717 Disabled"
            table.add_row(w.role, w.name, w.autonomy, w.model or "default", status)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        if 0 <= idx < len(self._workers):
            detail = self.query_one("#worker-detail", WorkerDetailPanel)
            detail.update_worker(self._workers[idx])
