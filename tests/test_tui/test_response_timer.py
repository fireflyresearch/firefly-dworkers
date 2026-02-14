"""Tests for the ResponseTimer utility.

Exercises all lifecycle methods, computed properties, and formatting
without any external dependencies — only ``time.monotonic`` is patched
where deterministic values are needed.
"""

from __future__ import annotations

import time
from unittest.mock import patch

from firefly_dworkers_cli.tui.response_timer import ResponseTimer


class TestInitialState:
    """Before ``start()`` is called, every property should be zero."""

    def test_initial_state(self) -> None:
        timer = ResponseTimer()
        assert timer.elapsed == 0.0
        assert timer.thinking_time == 0.0
        assert timer.streaming_time == 0.0


class TestStart:
    """Calling ``start()`` should begin timing."""

    def test_start_begins_timing(self) -> None:
        timer = ResponseTimer()
        timer.start()
        # Even a tiny sleep should produce a positive elapsed value.
        time.sleep(0.01)
        assert timer.elapsed > 0


class TestStop:
    """Calling ``stop()`` should freeze elapsed time."""

    def test_stop_freezes_elapsed(self) -> None:
        timer = ResponseTimer()
        timer.start()
        time.sleep(0.01)
        timer.stop()
        frozen = timer.elapsed
        time.sleep(0.02)
        assert timer.elapsed == frozen


class TestMarkFirstToken:
    """Tests for ``mark_first_token()``."""

    def test_mark_first_token(self) -> None:
        timer = ResponseTimer()
        timer.start()
        time.sleep(0.01)
        timer.mark_first_token()
        assert timer.thinking_time > 0
        assert timer.thinking_time < timer.elapsed

    def test_mark_first_token_idempotent(self) -> None:
        """A second call must not overwrite the first recorded value."""
        timer = ResponseTimer()
        timer.start()
        time.sleep(0.01)
        timer.mark_first_token()
        first_value = timer.thinking_time
        time.sleep(0.02)
        timer.mark_first_token()  # should be no-op
        assert timer.thinking_time == first_value

    def test_mark_first_token_before_start_is_noop(self) -> None:
        """Calling ``mark_first_token`` without ``start`` should not record."""
        timer = ResponseTimer()
        timer.mark_first_token()
        assert timer.thinking_time == 0.0


class TestStreamingTime:
    """Tests for the ``streaming_time`` property."""

    def test_streaming_time_requires_stop(self) -> None:
        """``streaming_time`` stays 0.0 until ``stop()`` is called."""
        timer = ResponseTimer()
        timer.start()
        timer.mark_first_token()
        assert timer.streaming_time == 0.0

    def test_streaming_time_after_stop(self) -> None:
        timer = ResponseTimer()
        timer.start()
        time.sleep(0.01)
        timer.mark_first_token()
        time.sleep(0.01)
        timer.stop()
        assert timer.streaming_time > 0


class TestFormatElapsed:
    """Tests for ``format_elapsed()``."""

    def test_format_elapsed(self) -> None:
        """Output must end with 's' and contain a decimal."""
        timer = ResponseTimer()
        timer.start()
        time.sleep(0.01)
        result = timer.format_elapsed()
        assert result.endswith("s")
        assert "." in result

    def test_format_elapsed_deterministic(self) -> None:
        """With a mocked clock the output is exact."""
        timer = ResponseTimer()
        with patch("firefly_dworkers_cli.tui.response_timer.time") as mock_time:
            mock_time.monotonic.side_effect = [100.0, 102.1]
            timer.start()
            result = timer.format_elapsed()
        assert result == "2.1s"


class TestFormatSummary:
    """Tests for ``format_summary(token_count)``."""

    def test_format_summary(self) -> None:
        timer = ResponseTimer()
        with patch("firefly_dworkers_cli.tui.response_timer.time") as mock_time:
            mock_time.monotonic.side_effect = [100.0, 102.1]
            timer.start()
            summary = timer.format_summary(1247)
        assert "total" in summary
        assert "\u00b7" in summary
        assert "tokens" in summary
        assert "1,247" in summary

    def test_format_summary_zero_tokens(self) -> None:
        timer = ResponseTimer()
        with patch("firefly_dworkers_cli.tui.response_timer.time") as mock_time:
            mock_time.monotonic.side_effect = [0.0, 0.5]
            timer.start()
            summary = timer.format_summary(0)
        assert "0 tokens" in summary

    def test_format_summary_large_count(self) -> None:
        timer = ResponseTimer()
        with patch("firefly_dworkers_cli.tui.response_timer.time") as mock_time:
            mock_time.monotonic.side_effect = [0.0, 3.0]
            timer.start()
            summary = timer.format_summary(1000000)
        assert "1,000,000" in summary


class TestFullLifecycle:
    """End-to-end lifecycle with deterministic mocked clock."""

    def test_full_lifecycle(self) -> None:
        timer = ResponseTimer()
        with patch("firefly_dworkers_cli.tui.response_timer.time") as mock_time:
            mock_time.monotonic.side_effect = [
                10.0,   # start
                12.0,   # mark_first_token
                15.0,   # stop
                15.0,   # elapsed query
            ]
            timer.start()
            timer.mark_first_token()
            timer.stop()

            assert timer.elapsed == 5.0
            assert timer.thinking_time == 2.0
            assert timer.streaming_time == 3.0
            assert timer.format_elapsed() == "5.0s"
            assert timer.format_summary(500) == "2.0s thinking \u00b7 5.0s total \u00b7 500 tokens \u00b7 167 tok/s"
