"""Tests for exit banner output."""

from datetime import UTC, datetime

from firefly_dworkers_cli.tui.app import DworkersApp
from firefly_dworkers_cli.tui.backend.models import Conversation


def _make_app() -> DworkersApp:
    app = DworkersApp.__new__(DworkersApp)
    app._conversation = None
    app._active_project = None
    app._total_tokens = 0
    return app


class TestExitBanner:
    def test_banner_includes_session_saved(self):
        app = _make_app()
        banner = app._build_exit_banner()
        assert "Session saved" in banner

    def test_banner_includes_conversation(self):
        app = _make_app()
        app._conversation = Conversation(
            id="c_abc123",
            title="Test Chat",
            participants=["user"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        banner = app._build_exit_banner()
        assert "c_abc123" in banner
        assert "Test Chat" in banner

    def test_banner_includes_resume_command(self):
        app = _make_app()
        app._conversation = Conversation(
            id="c_abc123",
            title="Test Chat",
            participants=["user"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        banner = app._build_exit_banner()
        assert "dworkers" in banner
        assert "c_abc123" in banner
