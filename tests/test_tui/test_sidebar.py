"""Test NavigationSidebar widget."""

from firefly_dworkers_cli.tui.widgets.sidebar import NavigationSidebar, NavItem

SAMPLE_SECTIONS = {
    "WORKSPACE": [
        ("dashboard", "Dashboard", "\u2302"),
        ("conversations", "Conversations", "\u25A1"),
    ],
    "MANAGE": [
        ("settings", "Settings", "\u2699"),
    ],
}


class TestNavigationSidebar:
    def test_instantiates(self):
        sidebar = NavigationSidebar(sections=SAMPLE_SECTIONS, active_id="dashboard")
        assert sidebar.active_id == "dashboard"

    def test_nav_item_instantiates(self):
        item = NavItem(screen_id="dashboard", label="Dashboard", icon="\u2302")
        assert item.screen_id == "dashboard"
