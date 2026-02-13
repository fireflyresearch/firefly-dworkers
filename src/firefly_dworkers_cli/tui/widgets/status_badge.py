"""Colored status badge widget."""

from __future__ import annotations

from textual.widgets import Static


class StatusBadge(Static):
    """Small colored badge for status indicators."""

    def __init__(self, text: str, variant: str = "default", **kwargs) -> None:
        css_class = {
            "success": "badge",
            "warning": "badge-warning",
            "error": "badge-error",
            "default": "badge",
        }.get(variant, "badge")
        super().__init__(text, classes=css_class, **kwargs)
