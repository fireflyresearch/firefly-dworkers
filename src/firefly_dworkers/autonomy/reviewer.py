from __future__ import annotations

from typing import Any

from firefly_dworkers.autonomy.checkpoint import CheckpointStore


class AutoApproveReviewer:
    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        return True


class PendingReviewer:
    def __init__(self, store: CheckpointStore):
        self._store = store

    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool:
        self._store.create(deliverable, worker_name=worker_name, phase=phase)
        return False
