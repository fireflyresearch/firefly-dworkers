from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CheckpointStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Checkpoint:
    id: str
    worker_name: str = ""
    phase: str = ""
    deliverable: Any = None
    status: CheckpointStatus = CheckpointStatus.PENDING
    rejection_reason: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None


class CheckpointStore:
    def __init__(self):
        self._checkpoints: dict[str, Checkpoint] = {}
        self._lock = threading.Lock()

    def submit(self, checkpoint_id: str, deliverable: Any, *, worker_name: str = "", phase: str = "") -> Checkpoint:
        cp = Checkpoint(id=checkpoint_id, worker_name=worker_name, phase=phase, deliverable=deliverable)
        with self._lock:
            self._checkpoints[checkpoint_id] = cp
        return cp

    def create(self, deliverable: Any, *, worker_name: str = "", phase: str = "") -> Checkpoint:
        checkpoint_id = str(uuid.uuid4())
        return self.submit(checkpoint_id, deliverable, worker_name=worker_name, phase=phase)

    def approve(self, checkpoint_id: str) -> None:
        with self._lock:
            cp = self._checkpoints[checkpoint_id]
            cp.status = CheckpointStatus.APPROVED
            cp.resolved_at = datetime.now(UTC)

    def reject(self, checkpoint_id: str, *, reason: str = "") -> None:
        with self._lock:
            cp = self._checkpoints[checkpoint_id]
            cp.status = CheckpointStatus.REJECTED
            cp.rejection_reason = reason
            cp.resolved_at = datetime.now(UTC)

    def is_pending(self, checkpoint_id: str) -> bool:
        with self._lock:
            cp = self._checkpoints.get(checkpoint_id)
            return cp is not None and cp.status == CheckpointStatus.PENDING

    def is_approved(self, checkpoint_id: str) -> bool:
        with self._lock:
            cp = self._checkpoints.get(checkpoint_id)
            return cp is not None and cp.status == CheckpointStatus.APPROVED

    def is_rejected(self, checkpoint_id: str) -> bool:
        with self._lock:
            cp = self._checkpoints.get(checkpoint_id)
            return cp is not None and cp.status == CheckpointStatus.REJECTED

    def get(self, checkpoint_id: str) -> Checkpoint | None:
        with self._lock:
            return self._checkpoints.get(checkpoint_id)

    def list_pending(self) -> list[Checkpoint]:
        with self._lock:
            return [cp for cp in self._checkpoints.values() if cp.status == CheckpointStatus.PENDING]

    def clear(self) -> None:
        with self._lock:
            self._checkpoints.clear()
