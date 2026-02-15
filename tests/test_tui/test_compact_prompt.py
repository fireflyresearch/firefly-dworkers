"""Tests for compact prompt CSS values."""

from firefly_dworkers_cli.tui.theme import APP_CSS


class TestCompactPromptCSS:
    def test_input_area_min_height_is_two(self):
        """Input area should be compact: min-height 2 (prompt + hint)."""
        assert "min-height: 2;" in APP_CSS

    def test_input_area_max_height_is_six(self):
        assert "max-height: 6;" in APP_CSS

    def test_prompt_max_height_is_five(self):
        """Prompt itself should max out at 5 lines."""
        assert "max-height: 5;" in APP_CSS
