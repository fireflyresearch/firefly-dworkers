"""Tests for the ThinkingIndicator widget.

All tests exercise internal state directly without mounting the widget
inside a Textual application, following the same pattern as the existing
widget tests in this project.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from firefly_dworkers_cli.tui.widgets.thinking_indicator import (
    SPINNER_FRAMES,
    ThinkingIndicator,
)


class _FakeTimer:
    """Minimal stand-in for ResponseTimer used by ``set_streaming_mode``."""

    def __init__(self, elapsed_text: str = "1.5s") -> None:
        self._text = elapsed_text

    def format_elapsed(self) -> str:
        return self._text


class TestThinkingIndicatorConstants:
    """Verify the module-level constant lists."""

    def test_spinner_frames_count(self) -> None:
        """Spinner frame list must have at least 4 entries."""
        assert len(SPINNER_FRAMES) >= 4

    def test_spinner_frames_are_dots(self) -> None:
        """Spinner should use simple dot animation."""
        for frame in SPINNER_FRAMES:
            assert all(c == "." or c == " " for c in frame), f"Frame '{frame}' contains non-dot characters"


class TestThinkingIndicatorInit:
    """Tests covering widget construction."""

    def test_instantiates_with_class(self) -> None:
        """The widget must carry the 'streaming-indicator' CSS class."""
        indicator = ThinkingIndicator()
        assert "streaming-indicator" in indicator.classes

    def test_initial_state(self) -> None:
        """Freshly created indicator should be in running state with zeroed index."""
        indicator = ThinkingIndicator()
        assert indicator._is_running is True
        assert indicator._spinner_index == 0
        assert indicator._timer is None


class TestTick:
    """Tests for the ``_tick`` method (animation callback)."""

    def test_animate_cycles_spinner(self) -> None:
        """A single ``_tick()`` call should advance the spinner index by 1."""
        indicator = ThinkingIndicator()
        assert indicator._spinner_index == 0
        indicator._tick()
        assert indicator._spinner_index == 1

    def test_animate_wraps_spinner(self) -> None:
        """Spinner index wraps around after exhausting all frames."""
        indicator = ThinkingIndicator()
        for _ in range(len(SPINNER_FRAMES)):
            indicator._tick()
        assert indicator._spinner_index == 0


class TestStop:
    """Tests for the ``stop()`` method."""

    def test_stop_halts_animation(self) -> None:
        """Calling ``stop()`` must set ``_is_running`` to False."""
        indicator = ThinkingIndicator()
        assert indicator._is_running is True
        indicator.stop()
        assert indicator._is_running is False

    def test_animate_after_stop_is_noop(self) -> None:
        """After ``stop()``, ``_tick()`` should not change spinner index."""
        indicator = ThinkingIndicator()
        indicator._tick()  # advance to index 1
        assert indicator._spinner_index == 1

        indicator.stop()
        indicator._tick()  # should be a no-op
        assert indicator._spinner_index == 1

    def test_stop_is_idempotent(self) -> None:
        """Calling ``stop()`` multiple times should not raise."""
        indicator = ThinkingIndicator()
        indicator.stop()
        indicator.stop()
        assert indicator._is_running is False


class TestSetStreamingMode:
    """Tests for the ``set_streaming_mode()`` method.

    These tests patch ``set_interval`` to avoid needing a running event loop,
    since the widget is not mounted in a Textual app.
    """

    def test_set_streaming_mode_stops_spinner(self) -> None:
        """Entering streaming mode must stop the thinking animation."""
        indicator = ThinkingIndicator()
        timer = _FakeTimer()
        with patch.object(indicator, "set_interval", return_value=MagicMock()):
            indicator.set_streaming_mode(timer)
        assert indicator._is_running is False
        assert indicator._timer is timer

    def test_set_streaming_mode_stores_timer(self) -> None:
        """The timer reference should be stored for elapsed display."""
        indicator = ThinkingIndicator()
        timer = _FakeTimer("2.3s")
        with patch.object(indicator, "set_interval", return_value=MagicMock()):
            indicator.set_streaming_mode(timer)
        assert indicator._timer is timer

    def test_set_streaming_mode_creates_elapsed_timer(self) -> None:
        """``set_streaming_mode`` should call ``set_interval`` for elapsed updates."""
        indicator = ThinkingIndicator()
        mock_interval = MagicMock()
        with patch.object(indicator, "set_interval", return_value=mock_interval) as mock_set:
            indicator.set_streaming_mode(_FakeTimer())
        mock_set.assert_called_once_with(0.5, indicator._update_elapsed)
        assert indicator._elapsed_timer is mock_interval

    def test_animate_noop_after_streaming_mode(self) -> None:
        """``_tick()`` should be a no-op once in streaming mode."""
        indicator = ThinkingIndicator()
        indicator._tick()  # index -> 1
        with patch.object(indicator, "set_interval", return_value=MagicMock()):
            indicator.set_streaming_mode(_FakeTimer())
        indicator._tick()  # no-op
        assert indicator._spinner_index == 1

    def test_update_elapsed_formats_correctly(self) -> None:
        """``_update_elapsed`` should produce the expected display string."""
        indicator = ThinkingIndicator()
        indicator._timer = _FakeTimer("3.7s")
        # Track what update() receives
        captured: list[str] = []
        original_update = indicator.update

        def spy_update(content: str = "") -> None:
            captured.append(str(content))
            original_update(content)

        indicator.update = spy_update  # type: ignore[assignment]
        indicator._update_elapsed()
        assert len(captured) == 1
        assert "\u00b7\u00b7\u00b7" in captured[0]
        assert "3.7s" in captured[0]
