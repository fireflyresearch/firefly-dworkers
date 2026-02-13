"""Tests for PlanBuilder and plan templates."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from firefly_dworkers.exceptions import PlanNotFoundError
from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.plans.builder import PlanBuilder
from firefly_dworkers.plans.registry import PlanRegistry
from firefly_dworkers.plans.templates.customer_segmentation import customer_segmentation_plan
from firefly_dworkers.plans.templates.market_analysis import market_analysis_plan
from firefly_dworkers.plans.templates.process_improvement import process_improvement_plan
from firefly_dworkers.plans.templates.technology_assessment import technology_assessment_plan
from firefly_dworkers.tenants.config import TenantConfig, WorkerConfig
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.analyst import AnalystWorker
from firefly_dworkers.workers.data_analyst import DataAnalystWorker
from firefly_dworkers.workers.manager import ManagerWorker
from firefly_dworkers.workers.researcher import ResearcherWorker


def _make_config() -> TenantConfig:
    """Helper to build a TenantConfig for testing."""
    return TenantConfig(
        id="test-tenant",
        name="Test Tenant",
        workers=WorkerConfig(),
    )


def _make_mock_worker(name: str = "mock-worker") -> MagicMock:
    """Create a mock worker that passes PipelineBuilder auto-wrapping."""
    mock = MagicMock()
    mock.name = name
    mock.run = MagicMock()  # Makes it agent-like for AgentStep wrapping
    return mock


# ---------------------------------------------------------------------------
# PlanRegistry tests
# ---------------------------------------------------------------------------


class TestPlanRegistry:
    """Test PlanRegistry operations."""

    def test_register_and_get(self) -> None:
        registry = PlanRegistry()
        plan = BasePlan("my-plan", description="desc")
        registry.register(plan)
        assert registry.get("my-plan") is plan

    def test_get_not_found(self) -> None:
        registry = PlanRegistry()
        with pytest.raises(PlanNotFoundError, match="no-such-plan"):
            registry.get("no-such-plan")

    def test_has(self) -> None:
        registry = PlanRegistry()
        plan = BasePlan("my-plan")
        registry.register(plan)
        assert registry.has("my-plan") is True
        assert registry.has("other") is False

    def test_list_plans(self) -> None:
        registry = PlanRegistry()
        registry.register(BasePlan("plan-a"))
        registry.register(BasePlan("plan-b"))
        names = registry.list_plans()
        assert "plan-a" in names
        assert "plan-b" in names

    def test_clear(self) -> None:
        registry = PlanRegistry()
        registry.register(BasePlan("plan-a"))
        registry.clear()
        assert registry.list_plans() == []
        assert registry.has("plan-a") is False


# ---------------------------------------------------------------------------
# PlanBuilder tests
# ---------------------------------------------------------------------------


class TestPlanBuilder:
    """Test PlanBuilder pipeline construction."""

    def test_build_creates_engine(self) -> None:
        from fireflyframework_genai.pipeline.engine import PipelineEngine

        plan = BasePlan("test-plan")
        plan.add_step(PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST))
        plan.add_step(
            PlanStep(step_id="s2", name="Step 2", worker_role=WorkerRole.RESEARCHER, depends_on=["s1"]),
        )

        config = _make_config()
        builder = PlanBuilder(plan, config)

        # Mock _create_worker to avoid needing API keys
        with patch.object(builder, "_create_worker", return_value=_make_mock_worker()):
            engine = builder.build()
        assert isinstance(engine, PipelineEngine)

    def test_build_dag_structure(self) -> None:
        plan = BasePlan("test-plan")
        plan.add_step(PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST))
        plan.add_step(PlanStep(step_id="s2", name="Step 2", worker_role=WorkerRole.RESEARCHER))
        plan.add_step(
            PlanStep(step_id="s3", name="Step 3", worker_role=WorkerRole.MANAGER, depends_on=["s1", "s2"]),
        )

        config = _make_config()
        builder = PlanBuilder(plan, config)
        dag = builder.build_dag()

        # Verify nodes
        assert "s1" in dag.nodes
        assert "s2" in dag.nodes
        assert "s3" in dag.nodes

        # Verify edges
        edge_pairs = [(e.source, e.target) for e in dag.edges]
        assert ("s1", "s3") in edge_pairs
        assert ("s2", "s3") in edge_pairs

    def test_worker_creation_per_role(self) -> None:
        plan = BasePlan("test-plan")
        plan.add_step(PlanStep(step_id="analyst-step", name="A", worker_role=WorkerRole.ANALYST))
        plan.add_step(PlanStep(step_id="researcher-step", name="R", worker_role=WorkerRole.RESEARCHER))
        plan.add_step(PlanStep(step_id="data-analyst-step", name="DA", worker_role=WorkerRole.DATA_ANALYST))
        plan.add_step(PlanStep(step_id="manager-step", name="M", worker_role=WorkerRole.MANAGER))

        config = _make_config()
        builder = PlanBuilder(plan, config, model=TestModel())

        analyst = builder._create_worker(plan.get_step("analyst-step"))
        assert isinstance(analyst, AnalystWorker)

        researcher = builder._create_worker(plan.get_step("researcher-step"))
        assert isinstance(researcher, ResearcherWorker)

        data_analyst = builder._create_worker(plan.get_step("data-analyst-step"))
        assert isinstance(data_analyst, DataAnalystWorker)

        manager = builder._create_worker(plan.get_step("manager-step"))
        assert isinstance(manager, ManagerWorker)

    def test_build_dag_uses_placeholders(self) -> None:
        """build_dag should not instantiate real workers."""
        plan = BasePlan("test-plan")
        plan.add_step(PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST))

        config = _make_config()
        builder = PlanBuilder(plan, config)
        dag = builder.build_dag()

        # The node should exist but its step should NOT be a real worker instance
        node = dag.nodes["s1"]
        assert not isinstance(node.step, AnalystWorker)

    def test_build_passes_retry_and_timeout(self) -> None:
        plan = BasePlan("test-plan")
        plan.add_step(
            PlanStep(
                step_id="s1",
                name="Step 1",
                worker_role=WorkerRole.ANALYST,
                retry_max=3,
                timeout_seconds=60,
            ),
        )

        config = _make_config()
        builder = PlanBuilder(plan, config)
        dag = builder.build_dag()

        node = dag.nodes["s1"]
        assert node.retry_max == 3
        assert node.timeout_seconds == 60


# ---------------------------------------------------------------------------
# Plan template tests
# ---------------------------------------------------------------------------


class TestPlanTemplates:
    """Test pre-built plan templates."""

    def test_customer_segmentation_plan(self) -> None:
        plan = customer_segmentation_plan()
        assert plan.name == "customer-segmentation"
        assert len(plan.steps) >= 4
        plan.validate()

        # Check key steps exist
        step_ids = [s.step_id for s in plan.steps]
        assert "gather-requirements" in step_ids
        assert "synthesize-report" in step_ids

    def test_market_analysis_plan(self) -> None:
        plan = market_analysis_plan()
        assert plan.name == "market-analysis"
        assert len(plan.steps) >= 4
        plan.validate()

    def test_process_improvement_plan(self) -> None:
        plan = process_improvement_plan()
        assert plan.name == "process-improvement"
        assert len(plan.steps) >= 4
        plan.validate()

    def test_technology_assessment_plan(self) -> None:
        plan = technology_assessment_plan()
        assert plan.name == "technology-assessment"
        assert len(plan.steps) >= 4
        plan.validate()

    def test_all_templates_registered(self) -> None:
        # Import templates to trigger registration
        import firefly_dworkers.plans.templates  # noqa: F401
        from firefly_dworkers.plans.registry import plan_registry

        assert plan_registry.has("customer-segmentation")
        assert plan_registry.has("market-analysis")
        assert plan_registry.has("process-improvement")
        assert plan_registry.has("technology-assessment")

    def test_template_plans_validate(self) -> None:
        """All templates should pass validation."""
        plans = [
            customer_segmentation_plan(),
            market_analysis_plan(),
            process_improvement_plan(),
            technology_assessment_plan(),
        ]
        for plan in plans:
            plan.validate()  # Should not raise

    def test_templates_use_multiple_roles(self) -> None:
        """Each template should use at least 2 different worker roles."""
        plans = [
            customer_segmentation_plan(),
            market_analysis_plan(),
            process_improvement_plan(),
            technology_assessment_plan(),
        ]
        for plan in plans:
            roles = {s.worker_role for s in plan.steps}
            assert len(roles) >= 2, f"Plan '{plan.name}' should use at least 2 roles, got {roles}"

    def test_templates_have_dependencies(self) -> None:
        """Each template should have at least some steps with dependencies."""
        plans = [
            customer_segmentation_plan(),
            market_analysis_plan(),
            process_improvement_plan(),
            technology_assessment_plan(),
        ]
        for plan in plans:
            has_deps = any(s.depends_on for s in plan.steps)
            assert has_deps, f"Plan '{plan.name}' should have steps with dependencies"
