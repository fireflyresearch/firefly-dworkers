"""Animated thinking indicator widget.

Displays a "Thinking ..." animation while the AI is processing,
then transitions to an elapsed-time display once token streaming begins.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from textual.widgets import Static

SPINNER_FRAMES = [".  ", ".. ", "...", ".. ", ".  ", "   "]


@runtime_checkable
class _HasFormatElapsed(Protocol):
    """Structural type for objects that expose ``format_elapsed()``."""

    def format_elapsed(self) -> str: ...


class ThinkingIndicator(Static):
    """Animated spinner that shows the AI is working.

    Displays ``Thinking ...`` with animated dots every ~100 ms.

    Call :meth:`set_streaming_mode` once the first response token arrives
    to switch to an elapsed-time counter, or :meth:`stop` to halt all
    animation.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            f"Thinking {SPINNER_FRAMES[0]}",
            classes="streaming-indicator",
            **kwargs,
        )
        self._spinner_index: int = 0
        self._spinner_timer: Any | None = None
        self._elapsed_timer: Any | None = None
        self._timer: _HasFormatElapsed | None = None
        self._is_running: bool = True

    # -- Lifecycle ------------------------------------------------------------

    def on_mount(self) -> None:  # noqa: D401
        """Start the animation loop once the widget is mounted."""
        if self._is_running:
            self._spinner_timer = self.set_interval(0.1, self._tick)

    # -- Animation ------------------------------------------------------------

    def _tick(self) -> None:
        """Advance the spinner one frame (called by the interval timer)."""
        if not self._is_running:
            return
        self._spinner_index = (self._spinner_index + 1) % len(SPINNER_FRAMES)
        self.update(f"Thinking {SPINNER_FRAMES[self._spinner_index]}")

    # -- Public API -----------------------------------------------------------

    def set_streaming_mode(self, timer: _HasFormatElapsed) -> None:
        """Switch from animated thinking to elapsed-time display.

        Parameters
        ----------
        timer:
            Any object exposing a ``format_elapsed() -> str`` method,
            typically a :class:`ResponseTimer`.
        """
        self._is_running = False
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
        self._timer = timer
        self._elapsed_timer = self.set_interval(0.5, self._update_elapsed)

    def _update_elapsed(self) -> None:
        """Refresh the display with the current elapsed time."""
        if self._timer is not None:
            self.update(f"\u00b7\u00b7\u00b7 {self._timer.format_elapsed()}")

    def stop(self) -> None:
        """Halt all animation timers."""
        self._is_running = False
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
        if self._elapsed_timer is not None:
            self._elapsed_timer.stop()
