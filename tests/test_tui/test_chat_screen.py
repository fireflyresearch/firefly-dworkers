"""Test ChatScreen (legacy screen, kept for backwards compatibility)."""

from firefly_dworkers_cli.tui.screens.chat import ChatHeader, ChatScreen


class TestChatScreen:
    def test_instantiates_without_conversation(self):
        screen = ChatScreen()
        assert screen._conversation is None

    def test_extract_role_from_mention(self):
        screen = ChatScreen()
        assert screen._extract_role("Hey @analyst check this") == "analyst"
        assert screen._extract_role("@researcher find info") == "researcher"
        assert screen._extract_role("@data_analyst run query") == "data_analyst"
        assert screen._extract_role("@manager assign tasks") == "manager"
        assert screen._extract_role("@designer create layout") == "designer"
        assert screen._extract_role("Just a question") is None

    def test_extract_role_unknown_mention_ignored(self):
        screen = ChatScreen()
        assert screen._extract_role("Hey @unknown do stuff") is None

    def test_extract_role_first_known_mention_wins(self):
        screen = ChatScreen()
        assert screen._extract_role("@researcher and @analyst") == "researcher"


class TestChatHeader:
    def test_instantiates(self):
        header = ChatHeader(title="Test Chat", tags=["fintech"], status="active")
        assert header._title == "Test Chat"

    def test_defaults(self):
        header = ChatHeader()
        assert header._title == "New Conversation"
        assert header._tags == []
        assert header._status == "active"

    def test_custom_tags_and_status(self):
        header = ChatHeader(title="Q4 Report", tags=["finance", "q4"], status="archived")
        assert header._tags == ["finance", "q4"]
        assert header._status == "archived"
