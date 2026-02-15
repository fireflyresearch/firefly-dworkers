"""Animated thinking indicator with rotating humorous verbs.

Displays a rotating fun verb (e.g. "Brewing coffee...") while the AI is
processing, then transitions to elapsed-time display once streaming begins.
"""

from __future__ import annotations

import random
from typing import Any, Protocol, runtime_checkable

from textual.widgets import Static

# Humorous verbs — rotate every ~3 seconds during inference.
THINKING_VERBS: list[str] = [
    "Thinking...",
    "Brewing coffee...",
    "Herding electrons...",
    "Consulting the hive mind...",
    "Summoning neurons...",
    "Calibrating intuition...",
    "Mining insights...",
    "Asking the senior dev...",
    "Reading the tea leaves...",
    "Connecting the dots...",
    "Sharpening pencils...",
    "Warming up the GPU...",
    "Channeling wisdom...",
    "Crunching numbers...",
    "Drafting blueprints...",
    "Waking up the intern...",
    "Polishing pixels...",
    "Consulting the rubber duck...",
    "Untangling spaghetti...",
    "Feeding the hamsters...",
]

# Rotating characters — cycles through symbols like Claude Code's spinner.
SPINNER_FRAMES = ["-", "\\", "|", "/", "-", "\\", "|", "/"]


@runtime_checkable
class _HasFormatElapsed(Protocol):
    """Structural type for objects that expose ``format_elapsed()``."""

    def format_elapsed(self) -> str: ...


class ThinkingIndicator(Static):
    """Animated spinner with rotating humorous verbs.

    Displays a random fun verb every ~3 seconds while the AI processes.
    Call :meth:`set_streaming_mode` once the first token arrives to switch
    to elapsed-time display, or :meth:`stop` to halt animation.
    """

    def __init__(self, **kwargs: Any) -> None:
        self._verb_pool = list(range(len(THINKING_VERBS)))
        random.shuffle(self._verb_pool)
        self._verb_index: int = 0
        self._spinner_index: int = 0
        verb = THINKING_VERBS[self._verb_pool[0]]
        super().__init__(
            f"  {SPINNER_FRAMES[0]} {verb}",
            classes="streaming-indicator",
            **kwargs,
        )
        self._spinner_timer: Any | None = None
        self._verb_timer: Any | None = None
        self._elapsed_timer: Any | None = None
        self._timer: _HasFormatElapsed | None = None
        self._is_thinking: bool = True

    def on_mount(self) -> None:
        """Start animation loops."""
        if self._is_thinking:
            self._spinner_timer = self.set_interval(0.08, self._tick_spinner)
            self._verb_timer = self.set_interval(3.5, self._rotate_verb)

    def _tick_spinner(self) -> None:
        """Advance the spinner one frame."""
        if not self._is_thinking:
            return
        self._spinner_index = (self._spinner_index + 1) % len(SPINNER_FRAMES)
        verb = THINKING_VERBS[self._verb_pool[self._verb_index]]
        frame = SPINNER_FRAMES[self._spinner_index]
        self.update(f"  {frame} {verb}")

    def _rotate_verb(self) -> None:
        """Switch to the next verb in the shuffled pool."""
        if not self._is_thinking:
            return
        self._verb_index = (self._verb_index + 1) % len(self._verb_pool)

    def set_streaming_mode(self, timer: _HasFormatElapsed) -> None:
        """Switch to elapsed-time display once the first token arrives."""
        self._is_thinking = False
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
        if self._verb_timer is not None:
            self._verb_timer.stop()
        self._timer = timer
        self._elapsed_timer = self.set_interval(0.5, self._update_elapsed)

    def _update_elapsed(self) -> None:
        """Refresh the display with the current elapsed time."""
        if self._timer is not None:
            self.update(f"  \u00b7\u00b7\u00b7 {self._timer.format_elapsed()}")

    def stop(self) -> None:
        """Halt all animation timers."""
        self._is_thinking = False
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
        if self._verb_timer is not None:
            self._verb_timer.stop()
        if self._elapsed_timer is not None:
            self._elapsed_timer.stop()
