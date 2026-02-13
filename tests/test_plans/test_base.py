"""Tests for PlanStep and BasePlan."""

from __future__ import annotations

import pytest

from firefly_dworkers.exceptions import PlanError, PlanNotFoundError
from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.types import WorkerRole

# ---------------------------------------------------------------------------
# PlanStep tests
# ---------------------------------------------------------------------------


class TestPlanStep:
    """Test PlanStep data model."""

    def test_create_step(self) -> None:
        step = PlanStep(
            step_id="gather-reqs",
            name="Gather Requirements",
            description="Collect business objectives",
            worker_role=WorkerRole.ANALYST,
        )
        assert step.step_id == "gather-reqs"
        assert step.name == "Gather Requirements"
        assert step.description == "Collect business objectives"
        assert step.worker_role == WorkerRole.ANALYST

    def test_step_defaults(self) -> None:
        step = PlanStep(
            step_id="s1",
            name="Step One",
            worker_role=WorkerRole.RESEARCHER,
        )
        assert step.description == ""
        assert step.prompt_template == ""
        assert step.depends_on == []
        assert step.retry_max == 0
        assert step.timeout_seconds == 0

    def test_step_with_dependencies(self) -> None:
        step = PlanStep(
            step_id="synthesize",
            name="Synthesize",
            worker_role=WorkerRole.ANALYST,
            depends_on=["research", "analyze"],
            retry_max=3,
            timeout_seconds=120,
        )
        assert step.depends_on == ["research", "analyze"]
        assert step.retry_max == 3
        assert step.timeout_seconds == 120


# ---------------------------------------------------------------------------
# BasePlan tests
# ---------------------------------------------------------------------------


class TestBasePlan:
    """Test BasePlan template class."""

    def test_create_plan(self) -> None:
        plan = BasePlan("test-plan", description="A test plan")
        assert plan.name == "test-plan"
        assert plan.description == "A test plan"
        assert plan.steps == []

    def test_create_plan_with_steps(self) -> None:
        steps = [
            PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST),
            PlanStep(step_id="s2", name="Step 2", worker_role=WorkerRole.RESEARCHER, depends_on=["s1"]),
        ]
        plan = BasePlan("test-plan", steps=steps)
        assert len(plan.steps) == 2
        assert plan.steps[0].step_id == "s1"
        assert plan.steps[1].step_id == "s2"

    def test_add_step(self) -> None:
        plan = BasePlan("test-plan")
        step = PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST)
        plan.add_step(step)
        assert len(plan.steps) == 1
        assert plan.steps[0] is step

    def test_get_step(self) -> None:
        plan = BasePlan("test-plan")
        step = PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST)
        plan.add_step(step)
        found = plan.get_step("s1")
        assert found is step

    def test_get_step_not_found(self) -> None:
        plan = BasePlan("test-plan")
        with pytest.raises(PlanNotFoundError, match="nonexistent"):
            plan.get_step("nonexistent")

    def test_validate_valid_plan(self) -> None:
        plan = BasePlan("test-plan")
        plan.add_step(PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST))
        plan.add_step(
            PlanStep(step_id="s2", name="Step 2", worker_role=WorkerRole.RESEARCHER, depends_on=["s1"]),
        )
        plan.add_step(
            PlanStep(step_id="s3", name="Step 3", worker_role=WorkerRole.MANAGER, depends_on=["s1", "s2"]),
        )
        # Should not raise
        plan.validate()

    def test_validate_missing_dependency(self) -> None:
        plan = BasePlan("test-plan")
        plan.add_step(PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST))
        plan.add_step(
            PlanStep(step_id="s2", name="Step 2", worker_role=WorkerRole.RESEARCHER, depends_on=["nonexistent"]),
        )
        with pytest.raises(PlanError, match="nonexistent"):
            plan.validate()

    def test_validate_empty_plan(self) -> None:
        plan = BasePlan("empty")
        # Empty plan is valid (no dependencies to violate)
        plan.validate()

    def test_validate_no_dependencies_plan(self) -> None:
        plan = BasePlan("parallel")
        plan.add_step(PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST))
        plan.add_step(PlanStep(step_id="s2", name="Step 2", worker_role=WorkerRole.RESEARCHER))
        # All independent steps — valid
        plan.validate()

    def test_steps_are_copied(self) -> None:
        """Verify that the steps list passed to __init__ is copied."""
        original = [PlanStep(step_id="s1", name="Step 1", worker_role=WorkerRole.ANALYST)]
        plan = BasePlan("test-plan", steps=original)
        original.append(PlanStep(step_id="s2", name="Step 2", worker_role=WorkerRole.RESEARCHER))
        assert len(plan.steps) == 1  # Not affected by mutation of original
