"""Navigation sidebar with grouped sections and active highlighting."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static


class NavItem(Static):
    """A single clickable navigation item."""

    class Clicked(Message):
        def __init__(self, screen_id: str) -> None:
            super().__init__()
            self.screen_id = screen_id

    def __init__(self, screen_id: str, label: str, icon: str = "", badge: int = 0) -> None:
        super().__init__(classes="nav-item")
        self.screen_id = screen_id
        self._label = label
        self._icon = icon
        self.badge = badge

    def compose(self) -> ComposeResult:
        badge_str = f" ({self.badge})" if self.badge > 0 else ""
        prefix = f"{self._icon} " if self._icon else "  "
        yield Label(f"{prefix}{self._label}{badge_str}")

    def on_click(self) -> None:
        self.post_message(self.Clicked(self.screen_id))

    def set_active(self, active: bool) -> None:
        self.set_class(active, "--active")


class NavigationSidebar(Vertical):
    """Sidebar with grouped navigation sections."""

    class Selected(Message):
        def __init__(self, screen_id: str) -> None:
            super().__init__()
            self.screen_id = screen_id

    active_id: reactive[str] = reactive("conversations")

    def __init__(
        self,
        sections: dict[str, list[tuple[str, str, str]]],
        active_id: str = "conversations",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._sections = sections
        self.active_id = active_id

    def compose(self) -> ComposeResult:
        yield Static("dworkers", classes="brand-title")
        yield Static("Digital Workers as a Service", classes="brand-subtitle")

        for section_name, items in self._sections.items():
            yield Static(section_name, classes="section-label")
            for screen_id, label, icon in items:
                yield NavItem(screen_id=screen_id, label=label, icon=icon)

        yield Static("", id="sidebar-spacer")
        yield Static("", id="user-panel")

    def on_mount(self) -> None:
        self._update_active()

    def on_nav_item_clicked(self, event: NavItem.Clicked) -> None:
        self.active_id = event.screen_id
        self.post_message(self.Selected(event.screen_id))

    def set_active(self, screen_id: str) -> None:
        self.active_id = screen_id

    def watch_active_id(self, new_id: str) -> None:
        self._update_active()

    def _update_active(self) -> None:
        for item in self.query(NavItem):
            item.set_active(item.screen_id == self.active_id)

    def set_badge(self, screen_id: str, count: int) -> None:
        for item in self.query(NavItem):
            if item.screen_id == screen_id:
                item.badge = count
                item.refresh()
                break
