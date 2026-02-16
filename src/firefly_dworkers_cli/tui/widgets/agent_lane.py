"""AgentLane widget — a scrollable per-agent pane for split-pane layout."""

from __future__ import annotations

from typing import Any

from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static


# Avatar colors per role for visual distinction
_ROLE_COLORS: dict[str, str] = {
    "analyst": "#60a5fa",
    "researcher": "#10b981",
    "data_analyst": "#c084fc",
    "manager": "#fbbf24",
    "content_writer": "#22d3ee",
    "strategist": "#f472b6",
}


class AgentLane(Vertical):
    """A per-agent lane with header bar and scrollable content area.

    Structure:
        AgentLane (Vertical)
        +-- Static (header: role name + status)
        +-- VerticalScroll (body: step_box content goes here)
    """

    def __init__(
        self,
        role: str,
        step_index: int,
        total_steps: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._role = role
        self._step_index = step_index
        self._total_steps = total_steps
        self._status: str = "waiting"  # waiting | running | complete | error
        self._tokens: int = 0
        self._duration_s: float = 0.0
        self._error_msg: str = ""

    def compose(self):
        """Compose the lane with header and scrollable body."""
        color = _ROLE_COLORS.get(self._role, "#888888")
        display_name = self._role.replace("_", " ").title()
        yield Static(
            f"[{color}]\u25cf {display_name}[/] ({self._step_index}/{self._total_steps})",
            classes="agent-lane-header",
            id=f"lane-header-{self._step_index}",
        )
        yield VerticalScroll(
            id=f"lane-body-{self._step_index}",
            classes="agent-lane-body",
        )

    @property
    def body(self) -> VerticalScroll:
        """Get the scrollable body container."""
        return self.query_one(f"#lane-body-{self._step_index}", VerticalScroll)

    def mark_running(self) -> None:
        """Set status to running."""
        self._status = "running"
        self.remove_class("agent-lane-waiting", "agent-lane-complete", "agent-lane-error")
        self.add_class("agent-lane-running")
        self._update_header()

    def mark_complete(self, tokens: int = 0, duration_s: float = 0.0) -> None:
        """Set status to complete with summary stats."""
        self._status = "complete"
        self._tokens = tokens
        self._duration_s = duration_s
        self.remove_class("agent-lane-waiting", "agent-lane-running", "agent-lane-error")
        self.add_class("agent-lane-complete")
        self._update_header()

    def mark_error(self, error_msg: str = "") -> None:
        """Set status to error."""
        self._status = "error"
        self._error_msg = error_msg
        self.remove_class("agent-lane-waiting", "agent-lane-running", "agent-lane-complete")
        self.add_class("agent-lane-error")
        self._update_header()

    def _completion_summary(self) -> str:
        """Format completion summary text."""
        tokens_fmt = f"{self._tokens:,}" if self._tokens else "0"
        dur_fmt = f"{self._duration_s:.1f}s" if self._duration_s else "0s"
        return f"\u2713 Complete \u2014 {tokens_fmt} tokens \u00b7 {dur_fmt}"

    def _update_header(self) -> None:
        """Update the header text based on status."""
        try:
            header = self.query_one(f"#lane-header-{self._step_index}", Static)
        except Exception:
            return
        color = _ROLE_COLORS.get(self._role, "#888888")
        display_name = self._role.replace("_", " ").title()
        if self._status == "complete":
            header.update(f"[{color}]\u25cf {display_name}[/]  {self._completion_summary()}")
        elif self._status == "error":
            header.update(f"[{color}]\u25cf {display_name}[/]  \u2717 Error")
        elif self._status == "running":
            header.update(
                f"[{color}]\u25cf {display_name}[/] ({self._step_index}/{self._total_steps})  \u00b7\u00b7\u00b7"
            )
        else:
            header.update(
                f"[{color}]\u25cf {display_name}[/] ({self._step_index}/{self._total_steps})"
            )
