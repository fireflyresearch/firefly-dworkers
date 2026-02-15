"""Tests for persistent popup widgets."""

from firefly_dworkers_cli.tui.app import CommandPopup, MentionPopup


class TestCommandPopup:
    def test_update_items_replaces_content(self):
        popup = CommandPopup()
        items = [("help", "Show help"), ("team", "List workers")]
        popup.update_items(items)
        assert popup._items == items
        assert popup._selected == 0

    def test_update_items_resets_selection(self):
        popup = CommandPopup()
        popup.update_items([("help", "Show help"), ("team", "List workers")])
        popup.move(1)
        assert popup._selected == 1
        popup.update_items([("new", "New conversation")])
        assert popup._selected == 0

    def test_selected_command_empty(self):
        popup = CommandPopup()
        assert popup.selected_command is None

    def test_selected_command_after_update(self):
        popup = CommandPopup()
        popup.update_items([("help", "Show help"), ("team", "List workers")])
        assert popup.selected_command == "help"
        popup.move(1)
        assert popup.selected_command == "team"

    def test_move_clamps_bounds(self):
        popup = CommandPopup()
        popup.update_items([("a", ""), ("b", ""), ("c", "")])
        popup.move(-1)
        assert popup._selected == 0
        popup.move(5)
        assert popup._selected == 2


class TestMentionPopup:
    def test_update_items(self):
        popup = MentionPopup()
        popup.update_items([("manager", "Team lead"), ("analyst", "Deep analysis")])
        assert popup._items == [("manager", "Team lead"), ("analyst", "Deep analysis")]

    def test_selected_role(self):
        popup = MentionPopup()
        popup.update_items([("manager", ""), ("analyst", "")])
        assert popup.selected_role == "manager"
        popup.move(1)
        assert popup.selected_role == "analyst"

    def test_selected_role_empty(self):
        popup = MentionPopup()
        assert popup.selected_role is None
