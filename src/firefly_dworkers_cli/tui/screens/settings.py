"""Settings screen — tenant, model, autonomy, and security configuration."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Input, Label, Select, Static, Switch

from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client


class TenantSwitcher(Horizontal):
    """Dropdown to switch between loaded tenants."""

    DEFAULT_CSS = """
    TenantSwitcher {
        height: 5;
        padding: 1 0;
    }
    """

    def __init__(self, tenants: list[str] | None = None, current: str = "default", **kwargs) -> None:
        super().__init__(**kwargs)
        self._tenants = tenants or ["default"]
        self._current = current

    def compose(self) -> ComposeResult:
        yield Label("Tenant: ")
        options = [(t, t) for t in self._tenants]
        yield Select(options, value=self._current, id="tenant-select")


class SettingsScreen(VerticalScroll):
    """Configuration screen for tenant settings."""

    DEFAULT_CSS = """
    SettingsScreen {
        height: 1fr;
        padding: 1 2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._client: DworkersClient | None = None

    def compose(self) -> ComposeResult:
        yield Static("\u2699 Settings", classes="panel-title")
        yield TenantSwitcher(id="tenant-switcher")
        yield Static("Models", classes="section-label")
        with Vertical(classes="stats-card"):
            yield Label("Default Model")
            yield Input(value="openai:gpt-4o", id="model-default")
            yield Label("Research Model")
            yield Input(value="", placeholder="Same as default", id="model-research")
            yield Label("Analysis Model")
            yield Input(value="", placeholder="Same as default", id="model-analysis")
        yield Static("Worker Autonomy", classes="section-label")
        yield DataTable(id="autonomy-table")
        yield Static("Security", classes="section-label")
        with Vertical(classes="stats-card"):
            with Horizontal():
                yield Label("Enable prompt guard")
                yield Switch(value=True, id="guard-prompt")
            with Horizontal():
                yield Label("Enable output guard")
                yield Switch(value=True, id="guard-output")
            with Horizontal():
                yield Label("Enable cost guard")
                yield Switch(value=True, id="guard-cost")
            yield Label("Cost budget (USD)")
            yield Input(value="0.00", id="cost-budget")
        yield Static("Branding", classes="section-label")
        with Vertical(classes="stats-card"):
            yield Label("Company Name")
            yield Input(value="", placeholder="Your company name", id="brand-company")
            yield Label("Report Template")
            yield Input(value="", placeholder="Template path", id="brand-template")
        yield Button("Save Settings", id="save-settings-btn", variant="primary")

    async def on_mount(self) -> None:
        self._client = await create_client()
        table = self.query_one("#autonomy-table", DataTable)
        table.add_columns("Role", "Autonomy Level", "Enabled")
        for role in ("analyst", "researcher", "data_analyst", "manager", "designer"):
            table.add_row(role, "semi_supervised", "\u2713")
