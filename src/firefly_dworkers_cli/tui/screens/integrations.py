"""Integrations screen — connector status and configuration."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.widgets.status_badge import StatusBadge

CONNECTOR_DEFINITIONS = [
    ("web_search", "Web Search", "search"),
    ("sharepoint", "SharePoint", "storage"),
    ("google_drive", "Google Drive", "storage"),
    ("confluence", "Confluence", "storage"),
    ("s3", "Amazon S3", "storage"),
    ("slack", "Slack", "messaging"),
    ("teams", "Microsoft Teams", "messaging"),
    ("email", "Email (SMTP)", "messaging"),
    ("jira", "Jira", "project_management"),
]


class ConnectorCard(Vertical):
    DEFAULT_CSS = """
    ConnectorCard { background: #2A2A3E; border: round #313244; padding: 1 2; height: 7; width: 1fr; }
    """

    def __init__(self, name: str, display_name: str, category: str, configured: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._name = name
        self._display_name = display_name
        self._category = category
        self._configured = configured

    def compose(self) -> ComposeResult:
        icon = "\u25CF" if self._configured else "\u25CB"
        yield Static(f"{icon} {self._display_name}", classes="panel-title")
        yield Static(self._category, classes="text-dim")
        status = "Connected" if self._configured else "Not configured"
        yield StatusBadge(status, variant="success" if self._configured else "error")
        yield Button("Configure", id=f"config-{self._name}")


class ConfigModal(ModalScreen):
    DEFAULT_CSS = """
    ConfigModal { align: center middle; }
    #config-dialog { width: 60; height: auto; max-height: 25; background: #2A2A3E; border: round #6C5CE7; padding: 2; }
    """

    def __init__(self, connector_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._connector_name = connector_name

    def compose(self) -> ComposeResult:
        with Vertical(id="config-dialog"):
            yield Static(f"Configure: {self._connector_name}", classes="panel-title")
            yield Label("API Key / Credential:")
            yield Input(placeholder="Enter credential...", password=True, id="cred-input")
            yield Label("Endpoint URL (optional):")
            yield Input(placeholder="https://...", id="endpoint-input")
            with Horizontal():
                yield Button("Save", id="save-config-btn", variant="primary")
                yield Button("Cancel", id="cancel-config-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-config-btn":
            self.dismiss(None)
        elif event.button.id == "save-config-btn":
            self.dismiss({"saved": True})


class IntegrationsScreen(Vertical):
    DEFAULT_CSS = """
    IntegrationsScreen { height: 1fr; padding: 1 2; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._client: DworkersClient | None = None

    def compose(self) -> ComposeResult:
        yield Static("\u2699 Integrations", classes="panel-title")
        categories: dict[str, list] = {}
        for name, display, category in CONNECTOR_DEFINITIONS:
            categories.setdefault(category, []).append((name, display))
        for cat_name, connectors in categories.items():
            yield Static(cat_name.replace("_", " ").title(), classes="section-label")
            with Grid(id=f"grid-{cat_name}"):
                for name, display in connectors:
                    yield ConnectorCard(name=name, display_name=display, category=cat_name)

    async def on_mount(self) -> None:
        self._client = await create_client()
        if self._client:
            statuses = await self._client.list_connectors()
            for status in statuses:
                for card in self.query(ConnectorCard):
                    if card._name == status.name:
                        card._configured = status.configured
                        card.refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("config-"):
            connector = btn_id.replace("config-", "")
            self.app.push_screen(ConfigModal(connector), callback=self._on_config_result)

    def _on_config_result(self, result: dict | None) -> None:
        if result:
            self.notify("Configuration saved", severity="information")
