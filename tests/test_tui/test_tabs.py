"""Tests for conversation tab management."""

from firefly_dworkers_cli.tui.app import ConversationTabBar


class TestConversationTabBar:
    def test_add_tab(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First Chat")
        assert bar._tabs == [("c1", "First Chat")]
        assert bar._active_id == "c1"

    def test_add_multiple_tabs(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First Chat")
        bar.add_tab("c2", "Second Chat")
        assert len(bar._tabs) == 2
        assert bar._active_id == "c2"

    def test_add_duplicate_tab_activates(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First")
        bar.add_tab("c2", "Second")
        bar.add_tab("c1", "First")  # duplicate
        assert len(bar._tabs) == 2  # no duplicate
        assert bar._active_id == "c1"  # but activates it

    def test_set_active(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First")
        bar.add_tab("c2", "Second")
        bar.set_active("c1")
        assert bar._active_id == "c1"

    def test_remove_tab(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First")
        bar.add_tab("c2", "Second")
        bar.remove_tab("c1")
        assert len(bar._tabs) == 1
        assert bar._tabs[0][0] == "c2"

    def test_remove_active_switches(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First")
        bar.add_tab("c2", "Second")
        bar.set_active("c2")
        bar.remove_tab("c2")
        assert bar._active_id == "c1"

    def test_tab_titles_truncated(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "A Very Long Conversation Title That Should Be Truncated")
        titles = bar.tab_titles()
        assert len(titles) == 1
        assert len(titles[0][1]) <= 22

    def test_next_tab(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First")
        bar.add_tab("c2", "Second")
        bar.add_tab("c3", "Third")
        bar.set_active("c1")
        bar.next_tab()
        assert bar._active_id == "c2"

    def test_next_tab_wraps(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "First")
        bar.add_tab("c2", "Second")
        bar.set_active("c2")
        bar.next_tab()
        assert bar._active_id == "c1"

    def test_next_tab_single(self):
        bar = ConversationTabBar()
        bar.add_tab("c1", "Only")
        bar.next_tab()
        assert bar._active_id == "c1"
