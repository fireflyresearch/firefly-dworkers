"""Tests for WorkerRegistry."""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from firefly_dworkers.exceptions import WorkerNotFoundError
from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.registry import WorkerRegistry, worker_registry


def _make_worker(name: str, role: WorkerRole = WorkerRole.ANALYST) -> BaseWorker:
    """Create a minimal BaseWorker for registry tests."""
    config = TenantConfig(id="reg-test", name="Registry Test")
    return BaseWorker(
        name,
        role=role,
        tenant_config=config,
        model=TestModel(),
        auto_register=False,
    )


class TestWorkerRegistry:
    """Test WorkerRegistry operations."""

    def test_register_and_get(self) -> None:
        registry = WorkerRegistry()
        worker = _make_worker("worker-a")
        registry.register(worker)
        assert registry.get("worker-a") is worker

    def test_get_missing_raises(self) -> None:
        registry = WorkerRegistry()
        with pytest.raises(WorkerNotFoundError):
            registry.get("nonexistent")

    def test_has_registered(self) -> None:
        registry = WorkerRegistry()
        worker = _make_worker("worker-b")
        registry.register(worker)
        assert registry.has("worker-b") is True

    def test_has_missing(self) -> None:
        registry = WorkerRegistry()
        assert registry.has("missing") is False

    def test_list_workers(self) -> None:
        registry = WorkerRegistry()
        registry.register(_make_worker("w1"))
        registry.register(_make_worker("w2"))
        registry.register(_make_worker("w3"))
        names = registry.list_workers()
        assert sorted(names) == ["w1", "w2", "w3"]

    def test_list_workers_empty(self) -> None:
        registry = WorkerRegistry()
        assert registry.list_workers() == []

    def test_clear(self) -> None:
        registry = WorkerRegistry()
        registry.register(_make_worker("to-clear"))
        assert registry.has("to-clear") is True
        registry.clear()
        assert registry.has("to-clear") is False
        assert registry.list_workers() == []

    def test_register_overwrites_existing(self) -> None:
        registry = WorkerRegistry()
        w1 = _make_worker("dup")
        w2 = _make_worker("dup")
        registry.register(w1)
        registry.register(w2)
        assert registry.get("dup") is w2

    def test_module_level_registry_exists(self) -> None:
        """Verify the module-level singleton exists."""
        assert isinstance(worker_registry, WorkerRegistry)
