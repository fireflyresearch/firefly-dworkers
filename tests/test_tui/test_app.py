"""Test DworkersApp chat-first shell."""

import asyncio

from firefly_dworkers_cli.tui.app import DworkersApp, _FALLBACK_ROLES
from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler


class TestDworkersApp:
    def test_app_instantiates(self):
        app = DworkersApp()
        assert app.TITLE == "dworkers"
        assert app._conversation is None
        assert app._total_tokens == 0
        assert app._is_streaming is False

    def test_fallback_roles(self):
        assert "analyst" in _FALLBACK_ROLES
        assert "researcher" in _FALLBACK_ROLES
        assert "data_analyst" in _FALLBACK_ROLES
        assert "manager" in _FALLBACK_ROLES
        assert "designer" in _FALLBACK_ROLES

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


class TestCheckpointHandlerInit:
    def test_checkpoint_handler_exists_at_init(self):
        app = DworkersApp()
        assert app._checkpoint_handler is not None
        assert isinstance(app._checkpoint_handler, TUICheckpointHandler)


class TestStreamingCancellation:
    def test_cancel_streaming_is_asyncio_event(self):
        app = DworkersApp()
        assert isinstance(app._cancel_streaming, asyncio.Event)

    def test_cancel_streaming_starts_unset(self):
        app = DworkersApp()
        assert not app._cancel_streaming.is_set()


class TestWorkerAvatarDisplay:
    def test_get_worker_display_with_cache(self):
        from firefly_dworkers_cli.tui.backend.models import WorkerInfo
        app = DworkersApp()
        app._worker_cache = [
            WorkerInfo(role="manager", name="Amara", avatar="A", avatar_color="green"),
        ]
        app._known_roles = {"manager", "amara"}
        app._name_to_role = {"amara": "manager"}
        name, avatar, color = app._get_worker_display("manager")
        assert name == "Amara"
        assert avatar == "A"
        assert color == "green"

    def test_get_worker_display_unknown_role(self):
        app = DworkersApp()
        app._worker_cache = []
        name, avatar, color = app._get_worker_display("unknown")
        assert name == "Unknown"
        assert avatar == ""
        assert color == ""

    def test_get_worker_display_fallback_name(self):
        from firefly_dworkers_cli.tui.backend.models import WorkerInfo
        app = DworkersApp()
        app._worker_cache = [
            WorkerInfo(role="data_analyst", name=""),
        ]
        name, avatar, color = app._get_worker_display("data_analyst")
        assert name == "Data Analyst"


class TestStatusBarSeparator:
    def test_no_pipe_separator_in_compose(self):
        """Status bar should use · not │ as separator."""
        import inspect
        source = inspect.getsource(DworkersApp.compose)
        assert "\u2502" not in source
        assert "·" in source


class TestSlashCommandDetection:
    def test_text_starting_with_slash_detected(self):
        app = DworkersApp()
        assert app._match_command_fragment("/he") == "he"
        assert app._match_command_fragment("/") == ""
        assert app._match_command_fragment("/help extra") is None
        assert app._match_command_fragment("hello") is None
        assert app._match_command_fragment("") is None


class TestNameBasedMentions:
    def test_extract_role_by_worker_name(self):
        app = DworkersApp()
        app._known_roles = {"manager", "analyst", "researcher", "data_analyst", "designer", "amara", "leo", "yuki", "kofi", "noor"}
        app._name_to_role = {"amara": "manager", "leo": "analyst", "yuki": "researcher", "kofi": "data_analyst", "noor": "designer"}
        assert app._extract_role("Hey @amara check this") == "manager"
        assert app._extract_role("@leo analyze this") == "analyst"
        assert app._extract_role("@yuki find info") == "researcher"
        assert app._extract_role("@kofi run query") == "data_analyst"
        assert app._extract_role("@noor create layout") == "designer"

    def test_extract_role_by_role_name_still_works(self):
        app = DworkersApp()
        app._known_roles = {"manager", "analyst", "amara", "leo"}
        app._name_to_role = {"amara": "manager", "leo": "analyst"}
        assert app._extract_role("Hey @manager check this") == "manager"
        assert app._extract_role("@analyst do stuff") == "analyst"

    def test_extract_role_name_takes_priority(self):
        app = DworkersApp()
        app._known_roles = {"manager", "amara"}
        app._name_to_role = {"amara": "manager"}
        assert app._extract_role("@amara and @manager") == "manager"
