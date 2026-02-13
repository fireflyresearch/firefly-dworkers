"""Templates screen — browse and execute plan templates."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.backend.models import PlanInfo
from firefly_dworkers_cli.tui.widgets.status_badge import StatusBadge


class PlanCard(ListItem):
    def __init__(self, plan: PlanInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self.plan = plan

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                yield Label(self.plan.name, classes="panel-title")
                yield StatusBadge(f"{self.plan.steps} steps", variant="default")
            yield Static(self.plan.description or "No description", classes="text-dim")
            roles = ", ".join(self.plan.worker_roles) if self.plan.worker_roles else "auto"
            yield Static(f"Workers: {roles}", classes="text-dim")


class PlanExecuteModal(ModalScreen):
    DEFAULT_CSS = """
    PlanExecuteModal { align: center middle; }
    #plan-modal { width: 60; height: auto; max-height: 30; background: #2A2A3E; border: round #6C5CE7; padding: 2; }
    """

    def __init__(self, plan: PlanInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self._plan = plan

    def compose(self) -> ComposeResult:
        with Vertical(id="plan-modal"):
            yield Static(f"Execute: {self._plan.name}", classes="panel-title")
            yield Static(self._plan.description or "", classes="text-dim")
            yield Label("Brief / Input:")
            yield Input(placeholder="Describe the project...", id="plan-input")
            with Horizontal():
                yield Button("Execute", id="execute-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "execute-btn":
            input_text = self.query_one("#plan-input", Input).value
            self.dismiss({"plan": self._plan.name, "input": input_text})


class TemplatesScreen(Vertical):
    DEFAULT_CSS = """
    TemplatesScreen { height: 1fr; padding: 1 2; }
    """

    def __init__(self, category: str = "reports", **kwargs) -> None:
        super().__init__(**kwargs)
        self._category = category
        self._client: DworkersClient | None = None
        self._plans: list[PlanInfo] = []

    def compose(self) -> ComposeResult:
        yield Static(f"\u2338 Templates — {self._category.title()}", classes="panel-title")
        with Horizontal(classes="toolbar"):
            yield Button("Reports", id="tab-reports")
            yield Button("Decks", id="tab-decks")
            yield Button("Memos", id="tab-memos")
        yield ListView(id="plans-list")

    async def on_mount(self) -> None:
        self._client = await create_client()
        await self._refresh_plans()

    async def _refresh_plans(self) -> None:
        if not self._client:
            return
        self._plans = await self._client.list_plans()
        list_view = self.query_one("#plans-list", ListView)
        list_view.clear()
        for plan in self._plans:
            list_view.append(PlanCard(plan))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, PlanCard):
            self.app.push_screen(PlanExecuteModal(event.item.plan), callback=self._on_plan_result)

    def _on_plan_result(self, result: dict | None) -> None:
        if result:
            self.notify(f"Executing plan: {result['plan']}")
