"""Test TUI widgets."""

from firefly_dworkers_cli.tui.widgets import ThinkingIndicator
from firefly_dworkers_cli.tui.widgets.thinking_indicator import (
    SPINNER_FRAMES,
    THINKING_VERBS,
)


class TestThinkingIndicator:
    def test_importable_from_package(self):
        assert ThinkingIndicator is not None

    def test_constants_exported(self):
        assert len(SPINNER_FRAMES) >= 4
        assert len(THINKING_VERBS) >= 4
