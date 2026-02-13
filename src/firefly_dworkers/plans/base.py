"""BasePlan and PlanStep -- data models for consulting plan templates.

A :class:`BasePlan` is a reusable template describing a multi-step consulting
workflow as a DAG.  Each node is a :class:`PlanStep` that specifies which
:class:`~firefly_dworkers.types.WorkerRole` should execute it and which other
steps it depends on.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from firefly_dworkers.exceptions import PlanError, PlanNotFoundError
from firefly_dworkers.types import WorkerRole


class PlanStep(BaseModel):
    """A step in a consulting plan.

    This is a *metadata* model -- it describes what the step does and which
    worker role should execute it, but does not contain an executor.
    """

    step_id: str
    name: str
    description: str = ""
    worker_role: WorkerRole
    prompt_template: str = ""  # Jinja2-style or f-string template
    depends_on: list[str] = Field(default_factory=list)  # step_ids this depends on
    retry_max: int = 0
    timeout_seconds: float = 0


class BasePlan:
    """A reusable consulting plan template.

    Plans define a DAG of steps where each step is executed by a worker.

    Parameters:
        name: Unique plan name.
        description: Human-readable description of the plan.
        steps: Optional initial list of :class:`PlanStep` instances.
    """

    def __init__(
        self,
        name: str,
        *,
        description: str = "",
        steps: list[PlanStep] | None = None,
    ) -> None:
        self._name = name
        self._description = description
        self._steps: list[PlanStep] = list(steps or [])

    @property
    def name(self) -> str:
        """The plan name."""
        return self._name

    @property
    def description(self) -> str:
        """Human-readable description."""
        return self._description

    @property
    def steps(self) -> list[PlanStep]:
        """The ordered list of steps in this plan."""
        return list(self._steps)

    def add_step(self, step: PlanStep) -> None:
        """Add a step to this plan."""
        self._steps.append(step)

    def get_step(self, step_id: str) -> PlanStep:
        """Get a step by ID.

        Raises:
            PlanNotFoundError: If no step with *step_id* exists.
        """
        for step in self._steps:
            if step.step_id == step_id:
                return step
        raise PlanNotFoundError(f"Step '{step_id}' not found in plan '{self._name}'")

    def validate(self) -> None:
        """Validate the plan.

        Checks that all ``depends_on`` references point to existing step IDs.

        Raises:
            PlanError: If a dependency references a non-existent step.
        """
        step_ids = {s.step_id for s in self._steps}
        for step in self._steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise PlanError(
                        f"Step '{step.step_id}' depends on '{dep}' which does not "
                        f"exist in plan '{self._name}'. Available: {sorted(step_ids)}"
                    )

    def __repr__(self) -> str:
        return f"BasePlan(name={self._name!r}, steps={len(self._steps)})"
