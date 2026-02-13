"""Main DworkersApp — shell with sidebar navigation and content switching."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import ContentSwitcher, Footer, Static

from firefly_dworkers_cli.tui.theme import APP_CSS
from firefly_dworkers_cli.tui.widgets.sidebar import NavigationSidebar


class DworkersApp(App):
    """Dworkers TUI — Digital Workers as a Service."""

    TITLE = "dworkers"
    CSS = APP_CSS

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+k", "command_palette", "Search", show=True),
        Binding("ctrl+n", "new_conversation", "New Chat", show=True),
        Binding("ctrl+1", "goto_dashboard", "Dashboard", show=False),
        Binding("ctrl+2", "goto_conversations", "Conversations", show=False),
        Binding("ctrl+3", "goto_deliverables", "Deliverables", show=False),
        Binding("ctrl+4", "goto_analytics", "Analytics", show=False),
        Binding("ctrl+5", "goto_team", "Team", show=False),
        Binding("ctrl+6", "goto_knowledge", "Knowledge", show=False),
        Binding("ctrl+7", "goto_integrations", "Integrations", show=False),
        Binding("ctrl+8", "goto_settings", "Settings", show=False),
    ]

    SECTIONS = {
        "WORKSPACE": [
            ("dashboard", "Dashboard", "\u2302"),
            ("conversations", "Conversations", "\u25A1"),
            ("deliverables", "Deliverables", "\u25A3"),
            ("analytics", "Analytics", "\u2261"),
        ],
        "TEMPLATES": [
            ("templates-reports", "Reports", "\u2338"),
            ("templates-decks", "Decks", "\u2338"),
            ("templates-memos", "Memos", "\u2338"),
        ],
        "MANAGE": [
            ("team", "Team", "\u263B"),
            ("knowledge", "Knowledge Base", "\u2630"),
            ("integrations", "Integrations", "\u2699"),
            ("settings", "Settings", "\u2699"),
        ],
    }

    current_screen_id: str = "conversations"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield NavigationSidebar(
                sections=self.SECTIONS,
                active_id=self.current_screen_id,
                id="sidebar",
            )
            yield ContentSwitcher(id="content", initial=self.current_screen_id)
        yield Footer()

    def on_mount(self) -> None:
        self._load_screen(self.current_screen_id)

    def on_navigation_sidebar_selected(
        self, event: NavigationSidebar.Selected
    ) -> None:
        self._switch_to(event.screen_id)

    def _switch_to(self, screen_id: str) -> None:
        self.current_screen_id = screen_id
        self._load_screen(screen_id)
        switcher = self.query_one("#content", ContentSwitcher)
        switcher.current = screen_id
        sidebar = self.query_one("#sidebar", NavigationSidebar)
        sidebar.set_active(screen_id)

    def _load_screen(self, screen_id: str) -> None:
        """Lazy-load a screen if not already mounted."""
        switcher = self.query_one("#content", ContentSwitcher)
        if switcher.query(f"#{screen_id}"):
            return
        widget = self._create_screen_widget(screen_id)
        switcher.mount(widget)

    def _create_screen_widget(self, screen_id: str) -> Static:
        """Import and instantiate the screen widget on demand."""
        match screen_id:
            case "dashboard":
                from firefly_dworkers_cli.tui.screens.dashboard import DashboardScreen

                return DashboardScreen(id=screen_id)
            case "conversations":
                from firefly_dworkers_cli.tui.screens.conversations import ConversationsScreen

                return ConversationsScreen(id=screen_id)
            case "deliverables":
                from firefly_dworkers_cli.tui.screens.deliverables import DeliverablesScreen

                return DeliverablesScreen(id=screen_id)
            case "analytics":
                from firefly_dworkers_cli.tui.screens.analytics import AnalyticsScreen

                return AnalyticsScreen(id=screen_id)
            case s if s.startswith("templates"):
                from firefly_dworkers_cli.tui.screens.templates import TemplatesScreen

                category = s.replace("templates-", "") if "-" in s else "reports"
                return TemplatesScreen(category=category, id=screen_id)
            case "team":
                from firefly_dworkers_cli.tui.screens.team import TeamScreen

                return TeamScreen(id=screen_id)
            case "knowledge":
                from firefly_dworkers_cli.tui.screens.knowledge import KnowledgeScreen

                return KnowledgeScreen(id=screen_id)
            case "integrations":
                from firefly_dworkers_cli.tui.screens.integrations import IntegrationsScreen

                return IntegrationsScreen(id=screen_id)
            case "settings":
                from firefly_dworkers_cli.tui.screens.settings import SettingsScreen

                return SettingsScreen(id=screen_id)
            case _:
                return Static(f"Unknown screen: {screen_id}", id=screen_id)

    def action_command_palette(self) -> None:
        from firefly_dworkers_cli.tui.widgets.search import SearchModal

        self.push_screen(SearchModal(), callback=self._on_command)

    def _on_command(self, result: str | None) -> None:
        if not result:
            return
        if result.startswith("goto:"):
            self._switch_to(result.replace("goto:", ""))
        elif result == "action:new-conversation":
            self._switch_to("conversations")
        elif result == "action:quit":
            self.exit()

    def action_new_conversation(self) -> None:
        self._switch_to("conversations")

    def action_goto_dashboard(self) -> None:
        self._switch_to("dashboard")

    def action_goto_conversations(self) -> None:
        self._switch_to("conversations")

    def action_goto_deliverables(self) -> None:
        self._switch_to("deliverables")

    def action_goto_analytics(self) -> None:
        self._switch_to("analytics")

    def action_goto_team(self) -> None:
        self._switch_to("team")

    def action_goto_knowledge(self) -> None:
        self._switch_to("knowledge")

    def action_goto_integrations(self) -> None:
        self._switch_to("integrations")

    def action_goto_settings(self) -> None:
        self._switch_to("settings")
