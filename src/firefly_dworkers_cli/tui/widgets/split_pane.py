# src/firefly_dworkers_cli/tui/widgets/split_pane.py
"""SplitPaneContainer — dynamic grid layout for parallel agent panes."""

from __future__ import annotations

from typing import Any

from textual.containers import Grid


def grid_dimensions(agent_count: int) -> tuple[int, int]:
    """Compute (columns, rows) for a given number of agents.

    - 1 agent  -> 1x1 (full width)
    - 2 agents -> 2x1 (side-by-side)
    - 3-4      -> 2x2 grid
    - 5-6      -> 3x2 grid
    """
    if agent_count <= 1:
        return (1, 1)
    elif agent_count == 2:
        return (2, 1)
    elif agent_count <= 4:
        return (2, 2)
    else:
        return (3, 2)


class SplitPaneContainer(Grid):
    """A grid container that holds AgentLane widgets.

    Dynamically sizes the grid based on the number of agents.
    Provides focus management for keyboard navigation between panes.
    """

    def __init__(self, agent_count: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._agent_count = agent_count
        self._focused_index: int = 0
        cols, rows = grid_dimensions(agent_count)
        self.styles.grid_size_columns = cols
        self.styles.grid_size_rows = rows

    def focus_next_lane(self) -> None:
        """Move focus to the next lane (wraps around)."""
        self._focused_index = (self._focused_index + 1) % self._agent_count
        self._apply_focus()

    def focus_prev_lane(self) -> None:
        """Move focus to the previous lane (wraps around)."""
        self._focused_index = (self._focused_index - 1) % self._agent_count
        self._apply_focus()

    def focus_lane(self, number: int) -> None:
        """Focus a specific lane by 1-indexed number."""
        idx = number - 1
        if 0 <= idx < self._agent_count:
            self._focused_index = idx
            self._apply_focus()

    def _apply_focus(self) -> None:
        """Apply focus styling to the current lane."""
        from firefly_dworkers_cli.tui.widgets.agent_lane import AgentLane

        lanes = list(self.query(AgentLane))
        for i, lane in enumerate(lanes):
            if i == self._focused_index:
                lane.add_class("agent-lane-focused")
                lane.body.focus()
            else:
                lane.remove_class("agent-lane-focused")
