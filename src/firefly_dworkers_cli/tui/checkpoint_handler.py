"""TUICheckpointHandler — bridges core autonomy checkpoints to the Textual TUI.

When a worker calls ``maybe_checkpoint()``, this handler:
1. Creates a Checkpoint in the store
2. Creates an asyncio.Event for this checkpoint
3. Awaits the event (worker blocks here)
4. When the user approves/rejects via slash command, the event is set
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from firefly_dworkers.autonomy.checkpoint import (
    Checkpoint,
    CheckpointStore,
)


class TUICheckpointHandler:
    """Checkpoint handler that pauses workers until TUI user approves/rejects."""

    def __init__(self) -> None:
        self._store = CheckpointStore()
        self._events: dict[str, asyncio.Event] = {}
        self._results: dict[str, bool] = {}

    async def on_checkpoint(
        self, worker_name: str, phase: str, deliverable: Any
    ) -> bool:
        """Called by worker's maybe_checkpoint(). Blocks until user decides."""
        checkpoint_id = uuid.uuid4().hex[:8]
        self._store.submit(
            checkpoint_id,
            deliverable,
            worker_name=worker_name,
            phase=phase,
        )
        event = asyncio.Event()
        self._events[checkpoint_id] = event
        self._results[checkpoint_id] = False

        await event.wait()

        return self._results.get(checkpoint_id, False)

    def approve(self, checkpoint_id: str) -> None:
        """Approve a pending checkpoint — resumes the worker."""
        self._store.approve(checkpoint_id)
        self._results[checkpoint_id] = True
        if checkpoint_id in self._events:
            self._events[checkpoint_id].set()

    def reject(self, checkpoint_id: str, *, reason: str = "") -> None:
        """Reject a pending checkpoint — worker handles the rejection."""
        self._store.reject(checkpoint_id, reason=reason)
        self._results[checkpoint_id] = False
        if checkpoint_id in self._events:
            self._events[checkpoint_id].set()

    def list_pending(self) -> list[Checkpoint]:
        """Return all pending checkpoints."""
        return self._store.list_pending()

    def get(self, checkpoint_id: str) -> Checkpoint | None:
        """Return a checkpoint by ID."""
        return self._store.get(checkpoint_id)
