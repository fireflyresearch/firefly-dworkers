"""Navigation sidebar widget — stub for Task 1, implemented in Task 2."""

from __future__ import annotations

from textual.message import Message
from textual.widgets import Static


class NavigationSidebar(Static):
    """Sidebar navigation with grouped sections.

    Full implementation comes in Task 2. This stub provides enough
    surface area for the app shell to instantiate and tests to pass.
    """

    class Selected(Message):
        """Posted when a nav item is clicked."""

        def __init__(self, screen_id: str) -> None:
            super().__init__()
            self.screen_id = screen_id

    def __init__(
        self,
        *,
        sections: dict[str, list[tuple[str, str, str]]],
        active_id: str = "",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.sections = sections
        self._active_id = active_id

    def set_active(self, screen_id: str) -> None:
        """Update the active nav item."""
        self._active_id = screen_id
