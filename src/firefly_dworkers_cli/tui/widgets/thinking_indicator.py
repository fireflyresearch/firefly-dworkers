"""Animated thinking indicator with rotating humorous verbs.

Displays a rotating fun verb (e.g. "Brewing coffee...") while the AI is
processing, then transitions to elapsed-time display once streaming begins.
"""

from __future__ import annotations

import random
from typing import Any, Protocol, runtime_checkable

from textual.widgets import Static

# (emoji, verb) pairs — rotate every ~3 seconds during inference.
THINKING_VERBS: list[tuple[str, str]] = [
    ("\U0001f9e0", "Thinking..."),
    ("\u2615", "Brewing coffee..."),
    ("\u26a1", "Herding electrons..."),
    ("\U0001f41d", "Consulting the hive mind..."),
    ("\U0001f9ec", "Summoning neurons..."),
    ("\U0001f3af", "Calibrating intuition..."),
    ("\u26cf\ufe0f", "Mining insights..."),
    ("\U0001f468\u200d\U0001f4bb", "Asking the senior dev..."),
    ("\U0001f375", "Reading the tea leaves..."),
    ("\U0001f517", "Connecting the dots..."),
    ("\u270f\ufe0f", "Sharpening pencils..."),
    ("\U0001f525", "Warming up the GPU..."),
    ("\U0001f52e", "Channeling wisdom..."),
    ("\U0001f522", "Crunching numbers..."),
    ("\U0001f4d0", "Drafting blueprints..."),
    ("\U0001f634", "Waking up the intern..."),
    ("\u2728", "Polishing pixels..."),
    ("\U0001f986", "Consulting the rubber duck..."),
    ("\U0001f35d", "Untangling spaghetti..."),
    ("\U0001f439", "Feeding the hamsters..."),
]

SPINNER_FRAMES = ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f"]


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
        emoji, verb = THINKING_VERBS[self._verb_pool[0]]
        super().__init__(
            f"  {emoji} {verb}",
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
        emoji, verb = THINKING_VERBS[self._verb_pool[self._verb_index]]
        frame = SPINNER_FRAMES[self._spinner_index]
        self.update(f"  {frame} {emoji} {verb}")

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
