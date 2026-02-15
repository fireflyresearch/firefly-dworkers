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


class _WorkerMeta:
    """Metadata stored alongside a registered worker class."""

    __slots__ = ("cls", "description", "tags")

    def __init__(self, cls: type, description: str = "", tags: list[str] | None = None) -> None:
        self.cls = cls
        self.description = description
        self.tags: list[str] = tags or []


class WorkerFactory:
    """Thread-safe factory mapping :class:`WorkerRole` to worker classes."""

    def __init__(self) -> None:
        self._workers: dict[WorkerRole, _WorkerMeta] = {}
        self._lock = threading.Lock()

    # -- Registration --------------------------------------------------------

    def register(
        self,
        role: WorkerRole,
        *,
        description: str = "",
        tags: list[str] | None = None,
    ) -> Any:
        """Decorator that registers a worker class for *role*.

        Parameters:
            role: The :class:`WorkerRole` to register.
            description: Human-readable description of the worker.
            tags: Optional tags for categorisation.

        Returns:
            The original class, unmodified.
        """

        def decorator(cls: type) -> type:
            with self._lock:
                existing = self._workers.get(role)
                if existing is not None and existing.cls is not cls:
                    raise ValueError(
                        f"Role '{role}' already registered to "
                        f"{existing.cls.__qualname__}; cannot register "
                        f"{cls.__qualname__}."
                    )
                self._workers[role] = _WorkerMeta(cls, description=description, tags=tags)
            return cls

        return decorator

    # -- Lookup & Creation ---------------------------------------------------

    def create(self, role: WorkerRole, tenant_config: TenantConfig, **kwargs: Any) -> BaseWorker:
        """Instantiate the worker registered for *role*.

        Raises:
            KeyError: If no worker is registered for *role*.
        """
        with self._lock:
            meta = self._workers.get(role)
        if meta is None:
            raise KeyError(f"No worker registered for role '{role}'. Available: {self.list_roles()}")
        return meta.cls(tenant_config, **kwargs)

    def get_class(self, role: WorkerRole) -> type:
        """Return the raw class for *role* without instantiating."""
        with self._lock:
            meta = self._workers.get(role)
        if meta is None:
            raise KeyError(f"No worker registered for role '{role}'.")
        return meta.cls

    def get_metadata(self, role: WorkerRole) -> _WorkerMeta:
        """Return the metadata for *role* without instantiating."""
        with self._lock:
            meta = self._workers.get(role)
        if meta is None:
            raise KeyError(f"No worker registered for role '{role}'.")
        return meta

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
