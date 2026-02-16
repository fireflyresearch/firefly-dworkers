"""Tests for the interactive question widget."""

import pytest

from firefly_dworkers_cli.tui.widgets.interactive_question import (
    InteractiveQuestion,
    OptionItem,
    QuestionInput,
)


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

    def test_format_display_shows_marker(self):
        q = InteractiveQuestion(
            question="Pick:", options=["First", "Second"]
        )
        display = q._format_options()
        assert "\u276f" in display
        assert "1." in display
        assert "2." in display

    def test_submit_answer_sets_answered(self):
        q = InteractiveQuestion(
            question="Pick:", options=["A", "B"]
        )
        assert q._answered is False
        q._submit_answer("A", 0)
        assert q._answered is True

    def test_submit_answer_idempotent(self):
        q = InteractiveQuestion(
            question="Pick:", options=["A", "B"]
        )
        q._submit_answer("A", 0)
        q._submit_answer("B", 1)  # no-op
        assert q._answered is True

    def test_question_input_subclass(self):
        inp = QuestionInput(placeholder="Type...")
        assert isinstance(inp, QuestionInput)


class TestClickableOptions:
    def test_option_item_stores_index_and_text(self):
        item = OptionItem("Alpha", 0)
        assert item._option_text == "Alpha"
        assert item._option_index == 0

    def test_option_item_stores_different_index(self):
        item = OptionItem("Beta", 1)
        assert item._option_index == 1
