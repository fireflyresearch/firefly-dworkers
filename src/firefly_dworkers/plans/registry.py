"""PlanRegistry -- thread-safe registry for plan templates."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from firefly_dworkers.exceptions import PlanNotFoundError

if TYPE_CHECKING:
    from firefly_dworkers.plans.base import BasePlan


class PlanRegistry:
    """Thread-safe registry for :class:`BasePlan` templates.

    Plans are stored by name and can be retrieved, listed, or cleared.
    A module-level singleton :data:`plan_registry` is provided for
    convenience.
    """

    def __init__(self) -> None:
        self._plans: dict[str, BasePlan] = {}
        self._lock = threading.Lock()

    def register(self, plan: BasePlan) -> None:
        """Register a plan by its ``name`` attribute."""
        with self._lock:
            self._plans[plan.name] = plan

    def get(self, name: str) -> BasePlan:
        """Return the plan with *name*, or raise :class:`PlanNotFoundError`."""
        with self._lock:
            if name not in self._plans:
                raise PlanNotFoundError(f"Plan '{name}' not found. Registered: {list(self._plans.keys())}")
            return self._plans[name]

    def has(self, name: str) -> bool:
        """Return ``True`` if a plan with *name* is registered."""
        with self._lock:
            return name in self._plans

    def list_plans(self) -> list[str]:
        """Return a list of all registered plan names."""
        with self._lock:
            return list(self._plans.keys())

    def clear(self) -> None:
        """Remove all registered plans."""
        with self._lock:
            self._plans.clear()


plan_registry = PlanRegistry()
