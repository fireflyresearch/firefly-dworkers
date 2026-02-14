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
        """Summary string showing thinking time and token rate."""
        parts = []
        if self.thinking_time > 0:
            parts.append(f"{self.thinking_time:.1f}s thinking")
        parts.append(f"{self.elapsed:.1f}s total")
        parts.append(f"{token_count:,} tokens")
        if self.streaming_time > 0 and token_count > 0:
            rate = token_count / self.streaming_time
            parts.append(f"{rate:.0f} tok/s")
        return " \u00b7 ".join(parts)
