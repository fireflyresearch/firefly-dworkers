"""Test DworkersApp chat-first shell."""

from firefly_dworkers_cli.tui.app import DworkersApp, _KNOWN_ROLES


class TestDworkersApp:
    def test_app_instantiates(self):
        app = DworkersApp()
        assert app.TITLE == "dworkers"
        assert app._conversation is None
        assert app._total_tokens == 0
        assert app._is_streaming is False

    def test_known_roles(self):
        assert "analyst" in _KNOWN_ROLES
        assert "researcher" in _KNOWN_ROLES
        assert "data_analyst" in _KNOWN_ROLES
        assert "manager" in _KNOWN_ROLES
        assert "designer" in _KNOWN_ROLES

    def test_extract_role_from_mention(self):
        app = DworkersApp()
        assert app._extract_role("Hey @analyst check this") == "analyst"
        assert app._extract_role("@researcher find info") == "researcher"
        assert app._extract_role("@data_analyst run query") == "data_analyst"
        assert app._extract_role("@manager assign tasks") == "manager"
        assert app._extract_role("@designer create layout") == "designer"
        assert app._extract_role("Just a question") is None

    def test_extract_role_unknown_mention_ignored(self):
        app = DworkersApp()
        assert app._extract_role("Hey @unknown do stuff") is None

    def test_extract_role_first_known_mention_wins(self):
        app = DworkersApp()
        assert app._extract_role("@researcher and @analyst") == "researcher"
