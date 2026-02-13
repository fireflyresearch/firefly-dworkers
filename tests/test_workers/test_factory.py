"""Tests for WorkerFactory."""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.analyst import AnalystWorker
from firefly_dworkers.workers.data_analyst import DataAnalystWorker
from firefly_dworkers.workers.factory import WorkerFactory, worker_factory
from firefly_dworkers.workers.manager import ManagerWorker
from firefly_dworkers.workers.researcher import ResearcherWorker


def _make_config() -> TenantConfig:
    return TenantConfig(id="factory-test", name="Factory Test")


class TestWorkerFactory:
    """Test WorkerFactory operations."""

    def test_register_and_create(self) -> None:
        factory = WorkerFactory()

        @factory.register(WorkerRole.ANALYST)
        class CustomAnalyst(AnalystWorker):
            pass

        config = _make_config()
        worker = factory.create(WorkerRole.ANALYST, config, model=TestModel())
        assert isinstance(worker, CustomAnalyst)

    def test_create_missing_raises(self) -> None:
        factory = WorkerFactory()
        with pytest.raises(KeyError, match="No worker registered"):
            factory.create(WorkerRole.ANALYST, _make_config())

    def test_get_class(self) -> None:
        factory = WorkerFactory()

        @factory.register(WorkerRole.RESEARCHER)
        class MyResearcher(ResearcherWorker):
            pass

        assert factory.get_class(WorkerRole.RESEARCHER) is MyResearcher

    def test_has(self) -> None:
        factory = WorkerFactory()

        @factory.register(WorkerRole.MANAGER)
        class MyManager(ManagerWorker):
            pass

        assert factory.has(WorkerRole.MANAGER) is True
        assert factory.has(WorkerRole.ANALYST) is False

    def test_list_roles(self) -> None:
        factory = WorkerFactory()

        @factory.register(WorkerRole.ANALYST)
        class A(AnalystWorker):
            pass

        @factory.register(WorkerRole.RESEARCHER)
        class R(ResearcherWorker):
            pass

        roles = factory.list_roles()
        assert WorkerRole.ANALYST in roles
        assert WorkerRole.RESEARCHER in roles

    def test_clear(self) -> None:
        factory = WorkerFactory()

        @factory.register(WorkerRole.ANALYST)
        class A(AnalystWorker):
            pass

        assert factory.has(WorkerRole.ANALYST) is True
        factory.clear()
        assert factory.has(WorkerRole.ANALYST) is False

    def test_decorator_returns_original_class(self) -> None:
        factory = WorkerFactory()

        @factory.register(WorkerRole.DATA_ANALYST)
        class OrigDA(DataAnalystWorker):
            pass

        assert OrigDA.__name__ == "OrigDA"
        assert factory.get_class(WorkerRole.DATA_ANALYST) is OrigDA

    def test_duplicate_registration_raises(self) -> None:
        """Registering a different class under the same role raises ValueError."""
        factory = WorkerFactory()

        @factory.register(WorkerRole.ANALYST)
        class First(AnalystWorker):
            pass

        with pytest.raises(ValueError, match="already registered"):

            @factory.register(WorkerRole.ANALYST)
            class Second(AnalystWorker):
                pass

    def test_idempotent_registration_same_class(self) -> None:
        """Re-registering the same class under the same role is allowed."""
        factory = WorkerFactory()

        @factory.register(WorkerRole.ANALYST)
        class MyAnalyst(AnalystWorker):
            pass

        # Should not raise -- same class, same role
        factory.register(WorkerRole.ANALYST)(MyAnalyst)
        assert factory.get_class(WorkerRole.ANALYST) is MyAnalyst

    def test_module_level_factory_exists(self) -> None:
        """The module-level singleton should exist."""
        assert isinstance(worker_factory, WorkerFactory)

    def test_module_level_factory_has_all_roles(self) -> None:
        """After importing workers, factory should have all five roles."""
        assert worker_factory.has(WorkerRole.ANALYST)
        assert worker_factory.has(WorkerRole.RESEARCHER)
        assert worker_factory.has(WorkerRole.DATA_ANALYST)
        assert worker_factory.has(WorkerRole.MANAGER)
        assert worker_factory.has(WorkerRole.DESIGNER)

    def test_module_level_factory_creates_correct_types(self) -> None:
        config = _make_config()
        analyst = worker_factory.create(WorkerRole.ANALYST, config, model=TestModel())
        assert isinstance(analyst, AnalystWorker)

        researcher = worker_factory.create(WorkerRole.RESEARCHER, config, model=TestModel())
        assert isinstance(researcher, ResearcherWorker)

        data_analyst = worker_factory.create(WorkerRole.DATA_ANALYST, config, model=TestModel())
        assert isinstance(data_analyst, DataAnalystWorker)

        manager = worker_factory.create(WorkerRole.MANAGER, config, model=TestModel())
        assert isinstance(manager, ManagerWorker)

        from firefly_dworkers.workers.designer import DocumentDesignerWorker

        designer = worker_factory.create(WorkerRole.DESIGNER, config, model=TestModel())
        assert isinstance(designer, DocumentDesignerWorker)

    def test_factory_passes_kwargs(self) -> None:
        config = _make_config()
        worker = worker_factory.create(
            WorkerRole.ANALYST,
            config,
            name="custom-analyst",
            model=TestModel(),
        )
        assert worker.name == "custom-analyst"
