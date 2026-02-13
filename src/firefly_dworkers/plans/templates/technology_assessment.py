"""Technology assessment plan template."""

from __future__ import annotations

from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.types import WorkerRole


def technology_assessment_plan() -> BasePlan:
    """Pre-built plan for technology assessment engagements.

    DAG structure::

        assess-current-tech
            |               |
        research-alternatives  analyze-tech-data
            |               |
        build-recommendations
            |
        assessment-report
            |
        governance-review
    """
    plan = BasePlan(
        "technology-assessment",
        description="Assess current technology, research alternatives, and build recommendations",
    )
    plan.add_step(
        PlanStep(
            step_id="assess-current-tech",
            name="Assess Current Technology",
            description="Audit existing technology stack, integrations, and capabilities",
            worker_role=WorkerRole.ANALYST,
        )
    )
    plan.add_step(
        PlanStep(
            step_id="research-alternatives",
            name="Research Alternatives",
            description="Research alternative technologies, vendors, and emerging solutions",
            worker_role=WorkerRole.RESEARCHER,
            depends_on=["assess-current-tech"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="analyze-tech-data",
            name="Analyze Technology Data",
            description="Analyze performance metrics, cost data, and usage patterns",
            worker_role=WorkerRole.DATA_ANALYST,
            depends_on=["assess-current-tech"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="build-recommendations",
            name="Build Recommendations",
            description="Synthesize research and data into technology recommendations",
            worker_role=WorkerRole.ANALYST,
            depends_on=["research-alternatives", "analyze-tech-data"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="assessment-report",
            name="Assessment Report",
            description="Compile findings into a technology assessment report with migration plan",
            worker_role=WorkerRole.ANALYST,
            depends_on=["build-recommendations"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="governance-review",
            name="Governance Review",
            description="Review assessment with governance board and coordinate approval process",
            worker_role=WorkerRole.MANAGER,
            depends_on=["assessment-report"],
        )
    )
    return plan
