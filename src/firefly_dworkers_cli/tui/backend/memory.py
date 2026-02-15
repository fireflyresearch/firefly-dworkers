"""Conversation-scoped memory for cross-worker fact sharing."""
from __future__ import annotations

from typing import Any

from firefly_dworkers.orchestration.workspace import ProjectWorkspace


class ConversationMemory:
    """Shared memory scoped to a conversation.

    Wraps ProjectWorkspace to provide conversation-level fact storage.
    """

    def __init__(self, conversation_id: str) -> None:
        self._conv_id = conversation_id
        self._workspace = ProjectWorkspace(f"conv:{conversation_id}")

    @property
    def conversation_id(self) -> str:
        return self._conv_id

    @property
    def memory(self):
        """Return the underlying MemoryManager for assignment to workers."""
        return self._workspace.memory

    def set_fact(self, key: str, value: Any) -> None:
        self._workspace.set_fact(key, value)

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self._workspace.get_fact(key, default)

    def get_all_facts(self) -> dict[str, Any]:
        return self._workspace.get_all_facts()

    def get_context(self) -> str:
        return self._workspace.get_context()

    def snapshot(self) -> dict:
        return {"conversation_id": self._conv_id, "facts": self.get_all_facts()}

    def restore(self, data: dict) -> None:
        for key, value in data.get("facts", {}).items():
            self.set_fact(key, value)
