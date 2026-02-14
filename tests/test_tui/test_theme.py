"""Tests for the TUI theme constants and CSS."""

from firefly_dworkers_cli.tui.theme import (
    APP_CSS,
    BG,
    BG_HEADER,
    BG_INPUT,
    BORDER,
    ERROR,
    SUCCESS,
    TEXT,
    TEXT_DIM,
    TEXT_MUTED,
)


class TestThemeConstants:
    def test_bg_is_true_black(self):
        assert BG == "#000000"

    def test_bg_header_is_true_black(self):
        assert BG_HEADER == "#000000"

    def test_bg_input_is_true_black(self):
        assert BG_INPUT == "#000000"

    def test_text_is_soft_gray(self):
        assert TEXT == "#d4d4d4"

    def test_text_dim(self):
        assert TEXT_DIM == "#666666"

    def test_text_muted(self):
        assert TEXT_MUTED == "#555555"

    def test_border_is_subtle(self):
        assert BORDER == "#333333"

    def test_success_is_green(self):
        assert SUCCESS == "#10b981"

    def test_error_is_red(self):
        assert ERROR == "#ef4444"

    def test_no_purple_in_css(self):
        assert "#6366f1" not in APP_CSS
        assert "#1a1a2e" not in APP_CSS
        assert "#16213e" not in APP_CSS

    def test_css_has_true_black_background(self):
        assert "#000000" in APP_CSS

    def test_no_round_borders_in_css(self):
        assert "border: round" not in APP_CSS
