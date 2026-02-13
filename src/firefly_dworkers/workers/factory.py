"""WorkerFactory -- decorator-based factory for worker classes.

Workers self-register when their module is imported by applying the
:func:`worker_factory.register` decorator.  The factory replaces the
hardcoded ``worker_map`` dict in :class:`PlanBuilder._create_worker`.

Example::

    @worker_factory.register(WorkerRole.ANALYST)
    class AnalystWorker(BaseWorker):
        ...

    # Later, in PlanBuilder:
    worker = worker_factory.create(WorkerRole.ANALYST, tenant_config, name="...")
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from firefly_dworkers.types import WorkerRole

if TYPE_CHECKING:
    from firefly_dworkers.tenants.config import TenantConfig
    from firefly_dworkers.workers.base import BaseWorker


class WorkerFactory:
    """Thread-safe factory mapping :class:`WorkerRole` to worker classes."""

    def __init__(self) -> None:
        self._workers: dict[WorkerRole, type] = {}
        self._lock = threading.Lock()

    # -- Registration --------------------------------------------------------

    def register(self, role: WorkerRole) -> Any:
        """Decorator that registers a worker class for *role*.

        Returns:
            The original class, unmodified.
        """

        def decorator(cls: type) -> type:
            with self._lock:
                existing = self._workers.get(role)
                if existing is not None and existing is not cls:
                    raise ValueError(
                        f"Role '{role}' already registered to "
                        f"{existing.__qualname__}; cannot register "
                        f"{cls.__qualname__}."
                    )
                self._workers[role] = cls
            return cls

        return decorator

    # -- Lookup & Creation ---------------------------------------------------

    def create(self, role: WorkerRole, tenant_config: TenantConfig, **kwargs: Any) -> BaseWorker:
        """Instantiate the worker registered for *role*.

        Raises:
            KeyError: If no worker is registered for *role*.
        """
        with self._lock:
            cls = self._workers.get(role)
        if cls is None:
            raise KeyError(f"No worker registered for role '{role}'. Available: {self.list_roles()}")
        return cls(tenant_config, **kwargs)

    def get_class(self, role: WorkerRole) -> type:
        """Return the raw class for *role* without instantiating."""
        with self._lock:
            cls = self._workers.get(role)
        if cls is None:
            raise KeyError(f"No worker registered for role '{role}'.")
        return cls

    def has(self, role: WorkerRole) -> bool:
        """Return ``True`` if a worker is registered for *role*."""
        with self._lock:
            return role in self._workers

    def list_roles(self) -> list[WorkerRole]:
        """Return all registered roles."""
        with self._lock:
            return list(self._workers.keys())

    def clear(self) -> None:
        """Remove all registrations (useful for testing)."""
        with self._lock:
            self._workers.clear()


worker_factory = WorkerFactory()
