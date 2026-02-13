"""Project workspace -- shared memory for multi-agent collaboration."""

from __future__ import annotations

import logging
from typing import Any

from fireflyframework_genai.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class ProjectWorkspace:
    """Shared workspace for a multi-agent project.

    Wraps a forked MemoryManager to provide project-scoped fact storage
    where workers can share findings.
    """

    def __init__(self, project_id: str, *, memory: MemoryManager | None = None) -> None:
        base_memory = memory or MemoryManager()
        self._memory = base_memory.fork(working_scope_id=f"project:{project_id}")
        self._project_id = project_id

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def memory(self) -> MemoryManager:
        return self._memory

    def set_fact(self, key: str, value: Any) -> None:
        """Store a fact in the project workspace."""
        self._memory.set_fact(key, value)

    def get_fact(self, key: str, default: Any = None) -> Any:
        """Retrieve a fact from the project workspace."""
        return self._memory.get_fact(key, default)

    def get_all_facts(self) -> dict[str, Any]:
        """Return all facts stored in the workspace."""
        return self._memory.working.to_dict()

    def get_context(self) -> str:
        """Return a human-readable summary of workspace contents."""
        return self._memory.get_working_context()
