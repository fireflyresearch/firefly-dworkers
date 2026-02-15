"""Tests for the consolidated status bar."""

from firefly_dworkers_cli.tui.app import DworkersApp


class TestStatusHints:
    def test_idle_hints(self):
        """Idle state shows enter/help hints."""
        hints = DworkersApp._format_status_hints(
            is_streaming=False,
            has_question=False,
            private_role=None,
        )
        assert "enter to send" in hints
        assert "/help" in hints

    def test_streaming_hints(self):
        """Streaming state shows esc to cancel."""
        hints = DworkersApp._format_status_hints(
            is_streaming=True,
            has_question=False,
            private_role=None,
        )
        assert "esc to cancel" in hints

    def test_question_hints(self):
        """Question active state shows navigation hints."""
        hints = DworkersApp._format_status_hints(
            is_streaming=False,
            has_question=True,
            private_role=None,
        )
        assert "↑↓" in hints
        assert "tab" in hints

    def test_private_mode_shows_role(self):
        hints = DworkersApp._format_status_hints(
            is_streaming=False,
            has_question=False,
            private_role="researcher",
        )
        assert "@researcher" in hints
