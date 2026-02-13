"""ToolRegistry -- decorator-based registry for tool classes.

Tools self-register when their module is imported by applying the
:func:`tool_registry.register` decorator.  The registry replaces
hardcoded ``if/elif`` branching in ``toolkits.py`` with a
lookup-based factory pattern.

Example::

    @tool_registry.register("tavily", category="web_search")
    class TavilySearchTool(WebSearchTool):
        ...

    # Later, in toolkit factory:
    tool = tool_registry.create("tavily", api_key="...")
"""

from __future__ import annotations

import threading
from typing import Any


class ToolRegistry:
    """Thread-safe registry mapping string keys to tool classes.

    Each entry stores the tool class alongside a *category* label
    (e.g. ``"web_search"``, ``"storage"``, ``"communication"``).
    """

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    # -- Registration --------------------------------------------------------

    def register(self, name: str, *, category: str = "general") -> Any:
        """Decorator that registers a tool class under *name*.

        Parameters:
            name: Unique key used for lookup (e.g. ``"tavily"``).
            category: Logical grouping (e.g. ``"web_search"``).

        Returns:
            The original class, unmodified.
        """

        def decorator(cls: type) -> type:
            with self._lock:
                if name in self._tools:
                    existing = self._tools[name]["cls"]
                    if existing is not cls:
                        raise ValueError(
                            f"Tool '{name}' already registered to "
                            f"{existing.__qualname__}; cannot register "
                            f"{cls.__qualname__}."
                        )
                self._tools[name] = {"cls": cls, "category": category}
            return cls

        return decorator

    # -- Lookup & Creation ---------------------------------------------------

    def create(self, name: str, **kwargs: Any) -> Any:
        """Instantiate a registered tool by *name*.

        Raises:
            KeyError: If *name* is not registered.
        """
        with self._lock:
            entry = self._tools.get(name)
        if entry is None:
            raise KeyError(f"Tool '{name}' not registered. Available: {self.list_tools()}")
        return entry["cls"](**kwargs)

    def get_class(self, name: str) -> type:
        """Return the raw class for *name* without instantiating."""
        with self._lock:
            entry = self._tools.get(name)
        if entry is None:
            raise KeyError(f"Tool '{name}' not registered. Available: {self.list_tools()}")
        return entry["cls"]

    def has(self, name: str) -> bool:
        """Return ``True`` if *name* is registered."""
        with self._lock:
            return name in self._tools

    def list_tools(self) -> list[str]:
        """Return all registered tool names."""
        with self._lock:
            return list(self._tools.keys())

    def list_by_category(self, category: str) -> list[str]:
        """Return tool names filtered by *category*."""
        with self._lock:
            return [name for name, entry in self._tools.items() if entry["category"] == category]

    def get_category(self, name: str) -> str:
        """Return the category of a registered tool."""
        with self._lock:
            entry = self._tools.get(name)
        if entry is None:
            raise KeyError(f"Tool '{name}' not registered.")
        return entry["category"]

    def clear(self) -> None:
        """Remove all registrations (useful for testing)."""
        with self._lock:
            self._tools.clear()


tool_registry = ToolRegistry()
