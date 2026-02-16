"""ToolBlock widget — collapsible tool call display with minimal/verbose modes."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static


# Key parameter to show for each tool type in minimal mode
_KEY_PARAMS: dict[str, list[str]] = {
    "Read": ["file_path"],
    "Write": ["file_path"],
    "Edit": ["file_path"],
    "Bash": ["command"],
    "Grep": ["pattern", "path"],
    "Glob": ["pattern", "path"],
    "WebFetch": ["url"],
    "WebSearch": ["query"],
}


class ToolBlock(Static):
    """A tool call display block with minimal and verbose modes."""

    def __init__(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        verbose: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._tool_name = tool_name
        self._params = params or {}
        self._verbose = verbose
        self._status: str = "running"  # running | complete | error
        self._duration_ms: int | None = None
        self._result_preview: str | None = None
        self._error_msg: str | None = None
        self._render()

    def _key_param_summary(self) -> str:
        """Extract the key parameter value for minimal display."""
        keys = _KEY_PARAMS.get(self._tool_name, [])
        parts = []
        for key in keys:
            val = self._params.get(key)
            if val is not None:
                s = str(val)
                if len(s) > 60:
                    s = s[:57] + "..."
                parts.append(s)
        return " ".join(parts)

    def _format_minimal(self) -> str:
        """Format a single-line minimal tool display."""
        summary = self._key_param_summary()
        label = f"\u2699 {self._tool_name}"
        if summary:
            label += f" {summary}"

        if self._status == "running":
            return f"{label}  \u00b7\u00b7\u00b7"
        elif self._status == "complete":
            dur = f"  {self._duration_ms}ms" if self._duration_ms else ""
            return f"{label}{dur} \u2713"
        else:  # error
            return f"{label}  \u2717"

    def _format_verbose(self) -> str:
        """Format a multi-line verbose tool display."""
        lines = [self._format_minimal()]
        if self._params:
            for k, v in self._params.items():
                s = str(v)
                if len(s) > 80:
                    s = s[:77] + "..."
                lines.append(f"    {k}: {s}")
        if self._result_preview:
            lines.append(f"    result: {self._result_preview}")
        if self._duration_ms is not None:
            lines.append(f"    duration: {self._duration_ms}ms")
        if self._error_msg:
            lines.append(f"    error: {self._error_msg}")
        return "\n".join(lines)

    def _render(self) -> None:
        """Re-render based on current mode and status."""
        text = self._format_verbose() if self._verbose else self._format_minimal()
        self.update(text)

    def mark_complete(
        self, duration_ms: int | None = None, result_preview: str | None = None
    ) -> None:
        """Mark the tool call as complete."""
        self._status = "complete"
        self._duration_ms = duration_ms
        self._result_preview = result_preview
        self._update_status_class()
        self._render()

    def mark_error(self, error_msg: str) -> None:
        """Mark the tool call as failed."""
        self._status = "error"
        self._error_msg = error_msg
        self._update_status_class()
        self._render()

    def set_verbose(self, verbose: bool) -> None:
        """Toggle verbose display."""
        self._verbose = verbose
        self._render()

    def _update_status_class(self) -> None:
        """Update CSS classes based on status."""
        for cls in ("tool-block-status-running", "tool-block-status-complete", "tool-block-status-error"):
            self.remove_class(cls)
        self.add_class(f"tool-block-status-{self._status}")
