"""Test DworkersApp chat-first shell."""

import asyncio

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

    def test_app_accepts_mode_parameter(self):
        app = DworkersApp(mode="local")
        assert app._mode == "local"

    def test_app_accepts_autonomy_override(self):
        app = DworkersApp(autonomy_override="autonomous")
        assert app._autonomy_override == "autonomous"

    def test_app_defaults(self):
        app = DworkersApp()
        assert app._mode == "auto"
        assert app._autonomy_override is None
        assert app._server_url is None

    def test_app_accepts_server_url(self):
        app = DworkersApp(mode="remote", server_url="https://example.com")
        assert app._mode == "remote"
        assert app._server_url == "https://example.com"

    def test_autonomy_override_applied_to_router(self):
        app = DworkersApp(autonomy_override="autonomous")
        assert app._router.autonomy_level == "autonomous"

    def test_autonomy_override_none_keeps_default(self):
        app = DworkersApp()
        assert app._router.autonomy_level == "semi_supervised"


class TestAsyncMessageMethods:
    def test_add_user_message_is_async(self):
        app = DworkersApp()
        assert asyncio.iscoroutinefunction(app._add_user_message)

    def test_add_system_message_is_async(self):
        app = DworkersApp()
        assert asyncio.iscoroutinefunction(app._add_system_message)


class TestStreamingCancellation:
    def test_cancel_streaming_is_asyncio_event(self):
        app = DworkersApp()
        assert isinstance(app._cancel_streaming, asyncio.Event)

    def test_cancel_streaming_starts_unset(self):
        app = DworkersApp()
        assert not app._cancel_streaming.is_set()
