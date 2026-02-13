"""Knowledge backend abstractions.

Defines the :class:`KnowledgeBackend` protocol and concrete
:class:`InMemoryKnowledgeBackend` adapter that wraps
:class:`MemoryManager` from the framework.  This allows
:class:`KnowledgeRepository` to work with any conforming backend
without a hard dependency on ``MemoryManager``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from fireflyframework_genai.memory.manager import MemoryManager


@runtime_checkable
class KnowledgeBackend(Protocol):
    """Protocol for knowledge storage backends.

    Any object implementing these methods can serve as the storage
    layer for :class:`KnowledgeRepository`.
    """

    def set_fact(self, key: str, value: Any) -> None:
        """Store a value under *key*."""
        ...

    def get_fact(self, key: str) -> Any | None:
        """Retrieve the value for *key*, or ``None`` if missing."""
        ...

    def iter_items(self) -> list[tuple[str, Any]]:
        """Return all ``(key, value)`` pairs."""
        ...

    def clear_all(self) -> None:
        """Remove all stored data."""
        ...


class InMemoryKnowledgeBackend:
    """Adapter that wraps :class:`MemoryManager` to satisfy :class:`KnowledgeBackend`.

    This is the default backend and preserves full backward compatibility
    with the original ``KnowledgeRepository(memory=...)`` pattern.
    """

    def __init__(self, memory: MemoryManager | None = None, *, scope_id: str = "knowledge") -> None:
        self._memory = memory or MemoryManager(working_scope_id=scope_id)

    def set_fact(self, key: str, value: Any) -> None:
        self._memory.set_fact(key, value)

    def get_fact(self, key: str) -> Any | None:
        return self._memory.get_fact(key)

    def iter_items(self) -> list[tuple[str, Any]]:
        return list(self._memory.working.items())

    def clear_all(self) -> None:
        self._memory.clear_working()

    @property
    def memory(self) -> MemoryManager:
        """Expose the underlying :class:`MemoryManager` for backward compatibility."""
        return self._memory
