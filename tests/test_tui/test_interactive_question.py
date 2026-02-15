"""Tests for the interactive question widget."""

import pytest

from firefly_dworkers_cli.tui.widgets.interactive_question import InteractiveQuestion


class TestInteractiveQuestion:
    def test_create_with_options(self):
        q = InteractiveQuestion(
            question="Pick one:",
            options=["Option A", "Option B", "Option C"],
        )
        assert q._question == "Pick one:"
        assert len(q._options) == 3
        assert q._selected == 0
        assert q._free_form is False

    def test_move_selection(self):
        q = InteractiveQuestion(
            question="Pick:", options=["A", "B", "C"]
        )
        q.move(1)
        assert q._selected == 1
        q.move(1)
        assert q._selected == 2
        q.move(1)  # clamp
        assert q._selected == 2

    def test_move_up_clamps(self):
        q = InteractiveQuestion(
            question="Pick:", options=["A", "B"]
        )
        q.move(-1)
        assert q._selected == 0

    def test_selected_option(self):
        q = InteractiveQuestion(
            question="Pick:", options=["Alpha", "Beta"]
        )
        assert q.selected_option == "Alpha"
        q.move(1)
        assert q.selected_option == "Beta"

    def test_toggle_free_form(self):
        q = InteractiveQuestion(
            question="Pick:", options=["A"]
        )
        assert q._free_form is False
        q.toggle_free_form()
        assert q._free_form is True
        q.toggle_free_form()
        assert q._free_form is False

    def test_format_display_shows_marker(self):
        q = InteractiveQuestion(
            question="Pick:", options=["First", "Second"]
        )
        display = q._format_options()
        assert "❯" in display
        assert "1." in display
        assert "2." in display
