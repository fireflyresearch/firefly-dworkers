"""Tests for smart message routing logic."""

from datetime import UTC, datetime

from firefly_dworkers_cli.tui.app import DworkersApp
from firefly_dworkers_cli.tui.backend.models import Conversation

_NOW = datetime.now(UTC)


def _make_app() -> DworkersApp:
    """Create a DworkersApp without running it."""
    app = DworkersApp.__new__(DworkersApp)
    app._private_role = None
    app._conversation = None
    app._known_roles = {"manager", "analyst", "researcher"}
    app._name_to_role = {}
    app._worker_cache = []
    return app


def _conv(participants: list[str]) -> Conversation:
    """Helper to build a Conversation with required datetime fields."""
    return Conversation(
        id="c1",
        title="test",
        created_at=_NOW,
        updated_at=_NOW,
        participants=participants,
    )


class TestResolveTargetRole:
    def test_explicit_mention_wins(self):
        app = _make_app()
        app._conversation = _conv(["user", "analyst", "researcher"])
        assert app._resolve_target_role("@researcher look into this") == "researcher"

    def test_private_mode_wins(self):
        app = _make_app()
        app._private_role = "analyst"
        assert app._resolve_target_role("hello") == "analyst"

    def test_single_invited_agent(self):
        app = _make_app()
        app._conversation = _conv(["user", "analyst"])
        assert app._resolve_target_role("do market analysis") == "analyst"

    def test_multiple_agents_routes_to_manager(self):
        app = _make_app()
        app._conversation = _conv(["user", "analyst", "researcher"])
        assert app._resolve_target_role("do market analysis") == "manager"

    def test_no_invites_defaults_to_manager(self):
        app = _make_app()
        assert app._resolve_target_role("hello") == "manager"

    def test_manager_in_participants_ignored(self):
        app = _make_app()
        app._conversation = _conv(["user", "manager", "analyst"])
        assert app._resolve_target_role("do analysis") == "analyst"

    def test_no_conversation_defaults_to_manager(self):
        app = _make_app()
        app._conversation = None
        assert app._resolve_target_role("hi") == "manager"
