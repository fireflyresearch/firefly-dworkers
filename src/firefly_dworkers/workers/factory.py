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

    __slots__ = (
        "cls",
        "description",
        "tags",
        "display_name",
        "avatar",
        "avatar_color",
        "tagline",
        "prompt_template",
        "prompt_kwargs",
    )

    def __init__(
        self,
        cls: type,
        description: str = "",
        tags: list[str] | None = None,
        display_name: str = "",
        avatar: str = "",
        avatar_color: str = "",
        tagline: str = "",
        prompt_template: str = "",
        prompt_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.cls = cls
        self.description = description
        self.tags: list[str] = tags or []
        self.display_name = display_name
        self.avatar = avatar
        self.avatar_color = avatar_color
        self.tagline = tagline
        self.prompt_template = prompt_template
        self.prompt_kwargs: dict[str, Any] = prompt_kwargs or {}


class WorkerFactory:
    """Thread-safe factory mapping :class:`WorkerRole` to worker classes."""

    def __init__(self) -> None:
        self._workers: dict[str | WorkerRole, _WorkerMeta] = {}
        self._lock = threading.Lock()

    # -- Registration --------------------------------------------------------

    def register(
        self,
        role: WorkerRole,
        *,
        description: str = "",
        tags: list[str] | None = None,
        display_name: str = "",
        avatar: str = "",
        avatar_color: str = "",
        tagline: str = "",
    ) -> Any:
        """Decorator that registers a worker class for *role*.

        Parameters:
            role: The :class:`WorkerRole` to register.
            description: Human-readable description of the worker.
            tags: Optional tags for categorisation.
            display_name: Human-friendly name for the worker persona.
            avatar: Single character or emoji used as the worker's avatar.
            avatar_color: CSS/Textual color name for the avatar.
            tagline: Short phrase describing the worker's personality or focus.

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
                self._workers[role] = _WorkerMeta(
                    cls,
                    description=description,
                    tags=tags,
                    display_name=display_name,
                    avatar=avatar,
                    avatar_color=avatar_color,
                    tagline=tagline,
                )
            return cls

        return decorator

    def register_dynamic(
        self,
        role: str,
        *,
        description: str = "",
        display_name: str = "",
        avatar: str = "",
        avatar_color: str = "",
        tagline: str = "",
        prompt_template: str = "",
        prompt_kwargs: dict[str, Any] | None = None,
        cls: type | None = None,
    ) -> None:
        """Register a custom agent at runtime (not via decorator).

        Parameters:
            role: Unique string identifier for the agent.
            description: Human-readable description of the agent.
            display_name: Human-friendly name for the agent persona.
            avatar: Single character or emoji used as the agent's avatar.
            avatar_color: CSS/Textual color name for the avatar.
            tagline: Short phrase describing the agent's personality or focus.
            prompt_template: Name of the prompt template to use.
            prompt_kwargs: Keyword arguments forwarded to the prompt template.
            cls: Worker class to instantiate; defaults to :class:`BaseWorker`.
        """
        if cls is None:
            from firefly_dworkers.workers.base import BaseWorker

            cls = BaseWorker
        meta = _WorkerMeta(
            cls=cls,
            description=description,
            display_name=display_name,
            avatar=avatar,
            avatar_color=avatar_color,
            tagline=tagline,
            prompt_template=prompt_template,
            prompt_kwargs=prompt_kwargs,
        )
        with self._lock:
            self._workers[role] = meta

    def unregister(self, role: str) -> None:
        """Remove a dynamically registered agent.

        Silently does nothing if *role* is not registered.
        """
        with self._lock:
            self._workers.pop(role, None)

    def has_role(self, role: str) -> bool:
        """Check if a role is registered (accepts plain strings)."""
        with self._lock:
            return role in self._workers

    # -- Lookup & Creation ---------------------------------------------------

    def create(self, role: str | WorkerRole, tenant_config: TenantConfig, **kwargs: Any) -> BaseWorker:
        """Instantiate the worker registered for *role*.

        Raises:
            KeyError: If no worker is registered for *role*.
        """
        with self._lock:
            meta = self._workers.get(role)
        if meta is None:
            raise KeyError(f"No worker registered for role '{role}'. Available: {self.list_roles()}")
        return meta.cls(tenant_config, **kwargs)

    def get_class(self, role: str | WorkerRole) -> type:
        """Return the raw class for *role* without instantiating."""
        with self._lock:
            meta = self._workers.get(role)
        if meta is None:
            raise KeyError(f"No worker registered for role '{role}'.")
        return meta.cls

    def get_metadata(self, role: str | WorkerRole) -> _WorkerMeta:
        """Return the metadata for *role* without instantiating."""
        with self._lock:
            meta = self._workers.get(role)
        if meta is None:
            raise KeyError(f"No worker registered for role '{role}'.")
        return meta

    def has(self, role: str | WorkerRole) -> bool:
        """Return ``True`` if a worker is registered for *role*."""
        with self._lock:
            return role in self._workers

    def list_roles(self) -> list[str | WorkerRole]:
        """Return all registered roles."""
        with self._lock:
            return list(self._workers.keys())

    def clear(self) -> None:
        """Remove all registrations (useful for testing)."""
        with self._lock:
            self._workers.clear()


worker_factory = WorkerFactory()
