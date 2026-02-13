"""WorkerRegistry -- thread-safe registry for worker instances."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from firefly_dworkers.exceptions import WorkerNotFoundError

if TYPE_CHECKING:
    from firefly_dworkers.workers.base import BaseWorker


class WorkerRegistry:
    """Thread-safe registry for :class:`BaseWorker` instances.

    Workers are stored by name and can be retrieved, listed, or cleared.
    A module-level singleton :data:`worker_registry` is provided for
    convenience.
    """

    def __init__(self) -> None:
        self._workers: dict[str, BaseWorker] = {}
        self._lock = threading.Lock()

    def register(self, worker: BaseWorker) -> None:
        """Register a worker by its ``name`` attribute."""
        with self._lock:
            self._workers[worker.name] = worker

    def get(self, name: str) -> BaseWorker:
        """Return the worker with *name*, or raise :class:`WorkerNotFoundError`."""
        with self._lock:
            if name not in self._workers:
                raise WorkerNotFoundError(f"Worker '{name}' not found. Registered: {list(self._workers.keys())}")
            return self._workers[name]

    def has(self, name: str) -> bool:
        """Return ``True`` if a worker with *name* is registered."""
        with self._lock:
            return name in self._workers

    def list_workers(self) -> list[str]:
        """Return a list of all registered worker names."""
        with self._lock:
            return list(self._workers.keys())

    def clear(self) -> None:
        """Remove all registered workers."""
        with self._lock:
            self._workers.clear()


worker_registry = WorkerRegistry()
