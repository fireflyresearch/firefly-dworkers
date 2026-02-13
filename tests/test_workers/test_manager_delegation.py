"""Tests for ManagerWorker delegation and PlanAndExecute integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from firefly_dworkers.tenants.config import TenantConfig, WorkerConfig
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.manager import ManagerWorker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    verticals: list[str] | None = None,
    autonomy: str = "semi_supervised",
    custom_instructions: str = "",
) -> TenantConfig:
    """Helper to build a TenantConfig for testing."""
    worker_settings = {
        "analyst": {"autonomy": autonomy, "custom_instructions": custom_instructions},
        "researcher": {"autonomy": autonomy, "custom_instructions": custom_instructions},
        "data_analyst": {"autonomy": autonomy, "custom_instructions": custom_instructions},
        "manager": {"autonomy": autonomy, "custom_instructions": custom_instructions},
    }
    return TenantConfig(
        id="test-tenant",
        name="Test Tenant",
        verticals=verticals or [],
        workers=WorkerConfig(**worker_settings),
    )


def _make_mock_specialist(name: str = "mock-specialist") -> MagicMock:
    """Create a mock specialist worker."""
    worker = MagicMock()
    worker.name = name
    worker.role = WorkerRole.ANALYST
    worker.memory = None
    mock_result = MagicMock()
    mock_result.output = f"output from {name}"
    worker.run = AsyncMock(return_value=mock_result)
    return worker


# ===========================================================================
# ManagerWorker Delegation tests
# ===========================================================================


class TestManagerAcceptsSpecialists:
    """Test that ManagerWorker accepts specialists parameter."""

    def test_manager_accepts_specialists(self) -> None:
        """ManagerWorker should accept an optional specialists parameter."""
        config = _make_config()
        specialists = [_make_mock_specialist("analyst-1"), _make_mock_specialist("researcher-1")]

        worker = ManagerWorker(
            config,
            model=TestModel(),
            auto_register=False,
            specialists=specialists,
        )

        assert worker.role == WorkerRole.MANAGER
        assert len(worker._specialists) == 2

    def test_manager_works_without_specialists(self) -> None:
        """ManagerWorker should work fine without specialists (backward compatible)."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        assert worker.role == WorkerRole.MANAGER
        assert worker._specialists == []

    def test_manager_description_updated(self) -> None:
        """ManagerWorker description should mention coordination."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        assert "coordinator" in worker.description.lower() or "specialist" in worker.description.lower()

    def test_manager_tags_include_delegation(self) -> None:
        """ManagerWorker tags should include delegation."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        assert "delegation" in worker.tags

    def test_manager_backward_compatible_creation(self) -> None:
        """ManagerWorker should be backward compatible with existing tests."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        assert worker.role == WorkerRole.MANAGER
        assert "manager" in worker.name
        assert "manager" in worker.tags
        assert "consulting" in worker.tags


class TestManagerCreatesRouter:
    """Test DelegationRouter creation."""

    def test_manager_creates_router_with_specialists(self) -> None:
        """Router property should create a DelegationRouter when specialists are set."""
        config = _make_config()
        specialists = [_make_mock_specialist("s1"), _make_mock_specialist("s2")]

        worker = ManagerWorker(
            config,
            model=TestModel(),
            auto_register=False,
            specialists=specialists,
        )

        mock_router = MagicMock()
        mock_dr_cls = MagicMock(return_value=mock_router)
        mock_cbs = MagicMock()
        mock_cs = MagicMock()
        mock_rrs = MagicMock()

        with patch(
            "firefly_dworkers.workers.manager._import_delegation",
            return_value=(mock_dr_cls, mock_cbs, mock_cs, mock_rrs),
        ):
            router = worker.router
            assert router is mock_router
            mock_dr_cls.assert_called_once()

    def test_manager_router_none_without_specialists(self) -> None:
        """Router property should return None when no specialists are set."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        assert worker.router is None

    def test_manager_router_handles_import_error(self) -> None:
        """Router should return None when DelegationRouter is not importable."""
        config = _make_config()
        specialists = [_make_mock_specialist()]
        worker = ManagerWorker(
            config,
            model=TestModel(),
            auto_register=False,
            specialists=specialists,
        )

        # The _create_router method handles ImportError internally
        # Since the real import may or may not work, we test via _create_router
        with patch(
            "firefly_dworkers.workers.manager._import_delegation",
            side_effect=ImportError("not available"),
        ):
            # Reset router so it's recreated
            worker._router = None
            router = worker.router
            assert router is None


class TestManagerSetSpecialists:
    """Test set_specialists method."""

    def test_manager_set_specialists_resets_router(self) -> None:
        """set_specialists should reset the cached router."""
        config = _make_config()
        specialists = [_make_mock_specialist()]

        worker = ManagerWorker(
            config,
            model=TestModel(),
            auto_register=False,
            specialists=specialists,
        )

        # Simulate a cached router
        worker._router = MagicMock()
        assert worker._router is not None

        # Reset specialists should clear the router
        new_specialists = [_make_mock_specialist("new-s1")]
        worker.set_specialists(new_specialists)

        assert worker._router is None
        assert len(worker._specialists) == 1
        assert worker._specialists[0].name == "new-s1"


class TestManagerDelegate:
    """Test the delegate() method."""

    @pytest.mark.anyio()
    async def test_manager_delegate_uses_router(self) -> None:
        """delegate() should use DelegationRouter when available."""
        config = _make_config()
        specialists = [_make_mock_specialist()]

        worker = ManagerWorker(
            config,
            model=TestModel(),
            auto_register=False,
            specialists=specialists,
        )

        mock_route_result = MagicMock()
        mock_route_result.output = "routed result"
        mock_router = MagicMock()
        mock_router.route = AsyncMock(return_value=mock_route_result)
        worker._router = mock_router

        result = await worker.delegate("Analyze market trends")

        mock_router.route.assert_called_once_with("Analyze market trends")
        assert result is mock_route_result

    @pytest.mark.anyio()
    async def test_manager_delegate_fallback_without_router(self) -> None:
        """delegate() should fall back to self.run() when no router is available."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        mock_result = MagicMock()
        mock_result.output = "direct result"
        worker.run = AsyncMock(return_value=mock_result)

        result = await worker.delegate("Do something")

        worker.run.assert_called_once_with("Do something")
        assert result is mock_result


class TestManagerPlanner:
    """Test PlanAndExecute integration."""

    def test_manager_planner_lazy_init(self) -> None:
        """Planner should be lazily initialized."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        # Initially, _planner is None
        assert worker._planner is None

        mock_planner = MagicMock()
        with patch(
            "firefly_dworkers.workers.manager._import_plan_and_execute",
            return_value=MagicMock(return_value=mock_planner),
        ):
            planner = worker.planner
            assert planner is mock_planner

    def test_manager_planner_none_on_import_error(self) -> None:
        """Planner should return None when PlanAndExecutePattern is not importable."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        with patch(
            "firefly_dworkers.workers.manager._import_plan_and_execute",
            side_effect=ImportError("not available"),
        ):
            planner = worker.planner
            assert planner is None

    @pytest.mark.anyio()
    async def test_manager_plan_and_execute(self) -> None:
        """plan_and_execute() should use PlanAndExecutePattern when available."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        mock_result = MagicMock()
        mock_result.output = "planned result"
        mock_result.success = True
        mock_result.steps_taken = 3

        mock_planner = MagicMock()
        mock_planner.execute = AsyncMock(return_value=mock_result)
        worker._planner = mock_planner

        result = await worker.plan_and_execute("Create market analysis plan")

        mock_planner.execute.assert_called_once_with(worker, input="Create market analysis plan")
        assert result is mock_result

    @pytest.mark.anyio()
    async def test_manager_plan_and_execute_fallback(self) -> None:
        """plan_and_execute() should fall back to self.run() when no planner."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)

        mock_result = MagicMock()
        mock_result.output = "direct result"
        worker.run = AsyncMock(return_value=mock_result)

        # Ensure planner returns None
        with patch(
            "firefly_dworkers.workers.manager._import_plan_and_execute",
            side_effect=ImportError("not available"),
        ):
            result = await worker.plan_and_execute("Plan something")

        worker.run.assert_called_once_with("Plan something")
        assert result is mock_result


class TestManagerDelegationStrategy:
    """Test delegation strategy options."""

    def test_manager_delegation_strategy_default(self) -> None:
        """Default delegation strategy should be 'content'."""
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        assert worker._delegation_strategy == "content"

    def test_manager_delegation_strategy_capability(self) -> None:
        """Should accept 'capability' strategy."""
        config = _make_config()
        worker = ManagerWorker(
            config,
            model=TestModel(),
            auto_register=False,
            delegation_strategy="capability",
        )
        assert worker._delegation_strategy == "capability"

    def test_manager_delegation_strategy_round_robin(self) -> None:
        """Should accept 'round_robin' strategy."""
        config = _make_config()
        worker = ManagerWorker(
            config,
            model=TestModel(),
            auto_register=False,
            delegation_strategy="round_robin",
        )
        assert worker._delegation_strategy == "round_robin"


# ===========================================================================
# Orchestrator DelegationRouter tests
# ===========================================================================


class TestOrchestratorDelegationRouter:
    """Test DelegationRouter integration in orchestrator."""

    def test_orchestrator_delegation_disabled_by_default(self) -> None:
        """Delegation should be disabled by default for backward compatibility."""
        from firefly_dworkers.orchestration.orchestrator import ProjectOrchestrator

        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="default-test")
        assert orch._get_delegation_router() is None

    @pytest.mark.anyio()
    async def test_orchestrator_uses_delegation_router(self) -> None:
        """Orchestrator should try DelegationRouter when delegation is enabled."""
        from firefly_dworkers.orchestration.orchestrator import ProjectOrchestrator

        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="delegation-test", enable_delegation=True)

        mock_route_result = MagicMock()
        mock_route_result.output = "routed output"

        mock_router = MagicMock()
        mock_router.route = AsyncMock(return_value=mock_route_result)

        # Patch _get_delegation_router to return a mock router
        with patch.object(orch, "_get_delegation_router", return_value=mock_router):
            result = await orch._execute_single_task("analyst", "Analyze trends")

        assert result == "routed output"
        mock_router.route.assert_called_once()

    @pytest.mark.anyio()
    async def test_orchestrator_falls_back_without_router(self) -> None:
        """Orchestrator should fall back to direct worker creation when no router."""
        from firefly_dworkers.orchestration.orchestrator import ProjectOrchestrator

        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="fallback-test")

        mock_worker = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "direct output"
        mock_worker.run = AsyncMock(return_value=mock_result)
        mock_worker.memory = None

        with (
            patch.object(orch, "_get_delegation_router", return_value=None),
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_factory,
        ):
            mock_factory.create.return_value = mock_worker
            result = await orch._execute_single_task("analyst", "Analyze trends")

        assert result == "direct output"
        mock_factory.create.assert_called_once()

    @pytest.mark.anyio()
    async def test_orchestrator_delegation_router_failure_falls_back(self) -> None:
        """When DelegationRouter.route() fails, orchestrator should fall back."""
        from firefly_dworkers.orchestration.orchestrator import ProjectOrchestrator

        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="router-fail-test", enable_delegation=True)

        mock_router = MagicMock()
        mock_router.route = AsyncMock(side_effect=RuntimeError("routing failed"))

        mock_worker = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "fallback output"
        mock_worker.run = AsyncMock(return_value=mock_result)
        mock_worker.memory = None

        with (
            patch.object(orch, "_get_delegation_router", return_value=mock_router),
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_factory,
        ):
            mock_factory.create.return_value = mock_worker
            result = await orch._execute_single_task("analyst", "Analyze trends")

        assert result == "fallback output"

    def test_orchestrator_get_delegation_router_returns_none_on_import_error(self) -> None:
        """_get_delegation_router should return None when imports fail."""
        from firefly_dworkers.orchestration.orchestrator import ProjectOrchestrator

        config = _make_config()
        orch = ProjectOrchestrator(config, project_id="import-fail-test", enable_delegation=True)

        # The method uses lazy imports that may fail
        # Ensure it returns None gracefully
        with patch(
            "firefly_dworkers.orchestration.orchestrator._import_delegation",
            side_effect=ImportError("not available"),
        ):
            router = orch._get_delegation_router()
            assert router is None
