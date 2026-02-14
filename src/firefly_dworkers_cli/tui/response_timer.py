"""Monotonic timer tracking the response lifecycle.

Tracks three phases: start (user sends message), first-token arrival
(thinking phase ends), and stop (streaming complete).  Used by the TUI
to display elapsed time in the ThinkingIndicator and status bar.
"""

from __future__ import annotations

import time


class ResponseTimer:
    """Tracks elapsed, thinking, and streaming durations for a single response."""

    def __init__(self) -> None:
        self._start: float | None = None
        self._first_token: float | None = None
        self._end: float | None = None

    # ── lifecycle ────────────────────────────────

    def start(self) -> None:
        """Mark the beginning of a response cycle."""
        self._start = time.monotonic()

    def mark_first_token(self) -> None:
        """Record when the first streaming token arrives.

        No-op if already marked.
        """
        if self._first_token is None and self._start is not None:
            self._first_token = time.monotonic()

    def stop(self) -> None:
        """Freeze the timer at the current instant."""
        if self._start is not None:
            self._end = time.monotonic()

    # ── properties ───────────────────────────────

    @property
    def elapsed(self) -> float:
        """Seconds since *start* (or to *stop* if stopped)."""
        if self._start is None:
            return 0.0
        end = self._end if self._end is not None else time.monotonic()
        return end - self._start

    @property
    def thinking_time(self) -> float:
        """Seconds from *start* to *first token*."""
        if self._start is None or self._first_token is None:
            return 0.0
        return self._first_token - self._start

    @property
    def streaming_time(self) -> float:
        """Seconds from *first token* to *end*."""
        if self._first_token is None or self._end is None:
            return 0.0
        return self._end - self._first_token

    # ── formatting ───────────────────────────────

    def format_elapsed(self) -> str:
        """Human-readable elapsed time, e.g. ``'2.1s'``."""
        return f"{self.elapsed:.1f}s"

    def format_summary(self, token_count: int) -> str:
        """Summary string, e.g. ``'Thought for 2.1s \u00b7 1,247 tokens'``."""
        return f"Thought for {self.format_elapsed()} \u00b7 {token_count:,} tokens"
