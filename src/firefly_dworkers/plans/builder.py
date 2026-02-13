"""PlanBuilder -- converts a BasePlan + TenantConfig into an executable pipeline.

Given a :class:`BasePlan` and :class:`TenantConfig`, creates the appropriate
workers and wires them into a framework :class:`PipelineBuilder` DAG.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fireflyframework_genai.pipeline.builder import PipelineBuilder
from fireflyframework_genai.pipeline.steps import CallableStep

from firefly_dworkers.plans.base import BasePlan, PlanStep

if TYPE_CHECKING:
    from fireflyframework_genai.pipeline.dag import DAG
    from fireflyframework_genai.pipeline.engine import PipelineEngine

    from firefly_dworkers.tenants.config import TenantConfig
    from firefly_dworkers.workers.base import BaseWorker


class PlanBuilder:
    """Converts a plan template into an executable PipelineEngine.

    Given a BasePlan and TenantConfig, creates the appropriate workers
    and wires them into a framework PipelineBuilder DAG.

    Parameters:
        plan: The plan template to build from.
        tenant_config: Tenant configuration providing model settings
            and worker config.
        model: Optional model override passed to all workers.
            Useful for testing (e.g. ``TestModel()``).
    """

    def __init__(
        self,
        plan: BasePlan,
        tenant_config: TenantConfig,
        *,
        model: Any = None,
    ) -> None:
        self._plan = plan
        self._tenant_config = tenant_config
        self._model = model

    def build(self) -> PipelineEngine:
        """Build an executable pipeline from the plan.

        Creates workers for each step based on ``worker_role``,
        wraps them as pipeline nodes (the framework auto-wraps
        :class:`FireflyAgent` as :class:`AgentStep`), and connects
        edges based on ``depends_on``.
        """
        pb = PipelineBuilder(self._plan.name)

        for step in self._plan.steps:
            worker = self._create_worker(step)
            pb.add_node(
                step.step_id,
                worker,
                retry_max=step.retry_max,
                timeout_seconds=step.timeout_seconds,
            )

        # Add edges based on dependencies
        for step in self._plan.steps:
            for dep_id in step.depends_on:
                pb.add_edge(dep_id, step.step_id)

        return pb.build()

    def build_dag(self) -> DAG:
        """Build just the DAG for inspection/visualization.

        Uses placeholder :class:`CallableStep` instances instead of real
        workers so that no heavyweight resources are created.
        """
        pb = PipelineBuilder(self._plan.name)

        for step in self._plan.steps:
            # Use a lightweight placeholder callable instead of a real worker
            placeholder = _make_placeholder(step.step_id)
            pb.add_node(
                step.step_id,
                placeholder,
                retry_max=step.retry_max,
                timeout_seconds=step.timeout_seconds,
            )

        for step in self._plan.steps:
            for dep_id in step.depends_on:
                pb.add_edge(dep_id, step.step_id)

        return pb.build_dag()

    def _create_worker(self, step: PlanStep) -> BaseWorker:
        """Create the appropriate worker for a step based on its role."""
        from firefly_dworkers.workers.factory import worker_factory

        kwargs: dict[str, Any] = {"name": f"{self._plan.name}-{step.step_id}"}
        if self._model is not None:
            kwargs["model"] = self._model
        return worker_factory.create(step.worker_role, self._tenant_config, **kwargs)


def _make_placeholder(step_id: str) -> CallableStep:
    """Create a no-op CallableStep placeholder for DAG inspection."""

    async def _noop(context: Any, inputs: dict[str, Any]) -> str:
        return f"placeholder-{step_id}"

    return CallableStep(_noop)
