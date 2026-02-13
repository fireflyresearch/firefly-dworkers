"""Process improvement plan template."""

from __future__ import annotations

from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.types import WorkerRole


def process_improvement_plan() -> BasePlan:
    """Pre-built plan for process improvement engagements.

    DAG structure::

        map-current-processes
            |                |
        research-best-practices  analyze-process-data
            |                |
        identify-improvements
            |
        improvement-report
            |
        stakeholder-review
    """
    plan = BasePlan(
        "process-improvement",
        description="Map current processes, identify gaps, and propose improvements",
    )
    plan.add_step(
        PlanStep(
            step_id="map-current-processes",
            name="Map Current Processes",
            description="Document existing workflows, identify inputs/outputs, and map process flows",
            worker_role=WorkerRole.ANALYST,
        )
    )
    plan.add_step(
        PlanStep(
            step_id="research-best-practices",
            name="Research Best Practices",
            description="Research industry best practices and benchmark against peer organizations",
            worker_role=WorkerRole.RESEARCHER,
            depends_on=["map-current-processes"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="analyze-process-data",
            name="Analyze Process Data",
            description="Analyze cycle times, throughput, error rates, and bottleneck metrics",
            worker_role=WorkerRole.DATA_ANALYST,
            depends_on=["map-current-processes"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="identify-improvements",
            name="Identify Improvements",
            description="Synthesize research and data to identify improvement opportunities",
            worker_role=WorkerRole.ANALYST,
            depends_on=["research-best-practices", "analyze-process-data"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="improvement-report",
            name="Improvement Report",
            description="Compile detailed recommendations with ROI projections and implementation roadmap",
            worker_role=WorkerRole.ANALYST,
            depends_on=["identify-improvements"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="stakeholder-review",
            name="Stakeholder Review",
            description="Present findings, gather feedback, and coordinate implementation planning",
            worker_role=WorkerRole.MANAGER,
            depends_on=["improvement-report"],
        )
    )
    return plan
