"""Inline task progress block — shows task tree with checkmarks and activity spinner.

Mounted in the chat area during plan execution. For simple chat (no plan),
falls back to just the thinking indicator line.
"""

from __future__ import annotations

import random
from typing import Any, Protocol, runtime_checkable

from textual.containers import Vertical
from textual.widgets import Static

from firefly_dworkers_cli.tui.widgets.thinking_indicator import (
    SPINNER_FRAMES,
    THINKING_VERBS,
)


@runtime_checkable
class _HasFormatElapsed(Protocol):
    def format_elapsed(self) -> str: ...


class TaskProgressBlock(Vertical):
    """Inline task progress with activity spinner and optional task tree."""

    def __init__(self, tasks: list[dict] | None = None, **kwargs: Any) -> None:
        super().__init__(classes="task-progress-block", **kwargs)
        self._tasks: list[dict] = tasks or []
        self._current_task: int | None = 0 if self._tasks else None
        self._verb_pool = list(range(len(THINKING_VERBS)))
        random.shuffle(self._verb_pool)
        self._verb_index: int = 0
        self._spinner_index: int = 0
        self._spinner_timer: Any | None = None
        self._verb_timer: Any | None = None
        self._elapsed_timer: Any | None = None
        self._timer: _HasFormatElapsed | None = None
        self._is_thinking: bool = True
        self._token_count: int = 0

    def on_mount(self) -> None:
        """Start animation loops."""
        self.mount(Static("", id="activity-line", classes="activity-line"))
        if self._tasks:
            self.mount(Static("", id="task-tree", classes="task-tree"))
        if self._is_thinking:
            self._spinner_timer = self.set_interval(0.08, self._tick)
            self._verb_timer = self.set_interval(3.5, self._rotate_verb)

    def _tick(self) -> None:
        """Advance spinner and refresh display."""
        if not self._is_thinking:
            return
        self._spinner_index = (self._spinner_index + 1) % len(SPINNER_FRAMES)
        self._refresh_display()

    def _rotate_verb(self) -> None:
        if not self._is_thinking:
            return
        self._verb_index = (self._verb_index + 1) % len(self._verb_pool)

    def _refresh_display(self) -> None:
        """Update the activity line and task tree."""
        emoji, verb = THINKING_VERBS[self._verb_pool[self._verb_index]]
        frame = SPINNER_FRAMES[self._spinner_index]
        activity = f"  {frame} {emoji} {verb}"
        try:
            self.query_one("#activity-line", Static).update(activity)
        except Exception:
            pass
        if self._tasks:
            try:
                self.query_one("#task-tree", Static).update(self._format_tree())
            except Exception:
                pass

    def _format_tree(self) -> str:
        """Render the task tree as a string with checkmarks and markers."""
        if not self._tasks:
            return ""
        lines = []
        for i, task in enumerate(self._tasks):
            if i == self._current_task:
                marker = "\u25a0"
                prefix = "  L "
            elif self._current_task is not None and i < self._current_task:
                marker = "\u2713"
                prefix = "    "
            else:
                marker = "\u25cb"
                prefix = "    "
            lines.append(f"{prefix}{marker} {task['name']}")
            for j, sub in enumerate(task.get("subtasks", [])):
                done = task.get("done", [])[j] if j < len(task.get("done", [])) else False
                if done:
                    lines.append(f"      \u2713 [s]{sub}[/s]")
                else:
                    lines.append(f"      \u25cb {sub}")
        return "\n".join(lines)

    # -- Public API -----------------------------------------------------------

    def mark_subtask_done(self, task_idx: int, subtask_idx: int) -> None:
        """Mark a subtask as completed."""
        if task_idx < len(self._tasks):
            done = self._tasks[task_idx].get("done", [])
            if subtask_idx < len(done):
                done[subtask_idx] = True
                self._refresh_display()

    def advance_task(self) -> None:
        """Move to the next task."""
        if self._current_task is not None and self._current_task < len(self._tasks) - 1:
            self._current_task += 1
            self._refresh_display()

    def update_token_count(self, count: int) -> None:
        """Update the displayed token count."""
        self._token_count = count
        self._refresh_display()

    def set_streaming_mode(self, timer: _HasFormatElapsed) -> None:
        """Switch to elapsed-time display once first token arrives."""
        self._is_thinking = False
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
        if self._verb_timer is not None:
            self._verb_timer.stop()
        self._timer = timer
        self._elapsed_timer = self.set_interval(0.5, self._update_elapsed)

    def _update_elapsed(self) -> None:
        if self._timer is not None:
            try:
                self.query_one("#activity-line", Static).update(
                    f"  \u00b7\u00b7\u00b7 {self._timer.format_elapsed()}"
                )
            except Exception:
                pass

    def stop(self) -> None:
        """Halt all animation."""
        self._is_thinking = False
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
        if self._verb_timer is not None:
            self._verb_timer.stop()
        if self._elapsed_timer is not None:
            self._elapsed_timer.stop()
