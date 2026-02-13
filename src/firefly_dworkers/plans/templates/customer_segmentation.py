"""Customer segmentation plan template."""

from __future__ import annotations

from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.types import WorkerRole


def customer_segmentation_plan() -> BasePlan:
    """Pre-built plan for customer segmentation analysis.

    DAG structure::

        gather-requirements
            |           |
        research-market  analyze-data
            |           |
        synthesize-report
            |
        project-review
    """
    plan = BasePlan(
        "customer-segmentation",
        description="Analyze customer data to identify segments and develop targeting strategies",
    )
    plan.add_step(
        PlanStep(
            step_id="gather-requirements",
            name="Gather Requirements",
            description="Collect business objectives, data sources, and segmentation criteria",
            worker_role=WorkerRole.ANALYST,
        )
    )
    plan.add_step(
        PlanStep(
            step_id="research-market",
            name="Market Research",
            description="Research industry benchmarks and segmentation best practices",
            worker_role=WorkerRole.RESEARCHER,
            depends_on=["gather-requirements"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="analyze-data",
            name="Data Analysis",
            description="Analyze customer data, build segments, generate statistical profiles",
            worker_role=WorkerRole.DATA_ANALYST,
            depends_on=["gather-requirements"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="synthesize-report",
            name="Synthesis & Report",
            description="Combine market research and data analysis into actionable recommendations",
            worker_role=WorkerRole.ANALYST,
            depends_on=["research-market", "analyze-data"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="project-review",
            name="Project Review",
            description="Review deliverables, coordinate stakeholder feedback",
            worker_role=WorkerRole.MANAGER,
            depends_on=["synthesize-report"],
        )
    )
    return plan
