"""Project workspace -- shared memory for multi-agent collaboration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
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

    def snapshot(self) -> dict:
        """Serialize workspace state for persistence."""
        return {"project_id": self._project_id, "facts": self.get_all_facts()}

    def restore(self, data: dict) -> None:
        """Restore workspace state from snapshot."""
        for key, value in data.get("facts", {}).items():
            self.set_fact(key, value)

    def save_to_file(self, path: Path) -> None:
        """Save workspace snapshot to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.snapshot(), indent=2, default=str))

    def load_from_file(self, path: Path) -> None:
        """Load workspace snapshot from JSON file."""
        if path.exists():
            data = json.loads(path.read_text())
            self.restore(data)
