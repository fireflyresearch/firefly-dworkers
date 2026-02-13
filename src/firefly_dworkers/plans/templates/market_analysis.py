"""Market analysis plan template."""

from __future__ import annotations

from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.types import WorkerRole


def market_analysis_plan() -> BasePlan:
    """Pre-built plan for market analysis.

    DAG structure::

        define-scope
            |
        research-competitors  analyze-market-data
            |                     |
        assess-opportunities
            |
        strategy-report
            |
        executive-review
    """
    plan = BasePlan(
        "market-analysis",
        description="Research competitors, analyze market size, and generate strategy report",
    )
    plan.add_step(
        PlanStep(
            step_id="define-scope",
            name="Define Scope",
            description="Define target markets, geographies, and competitive landscape boundaries",
            worker_role=WorkerRole.ANALYST,
        )
    )
    plan.add_step(
        PlanStep(
            step_id="research-competitors",
            name="Competitive Research",
            description="Research key competitors, their offerings, strengths, and weaknesses",
            worker_role=WorkerRole.RESEARCHER,
            depends_on=["define-scope"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="analyze-market-data",
            name="Market Data Analysis",
            description="Analyze market size, growth rates, and demographic trends",
            worker_role=WorkerRole.DATA_ANALYST,
            depends_on=["define-scope"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="assess-opportunities",
            name="Opportunity Assessment",
            description="Identify market gaps and strategic opportunities from research and data",
            worker_role=WorkerRole.ANALYST,
            depends_on=["research-competitors", "analyze-market-data"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="strategy-report",
            name="Strategy Report",
            description="Compile findings into a comprehensive market strategy report",
            worker_role=WorkerRole.ANALYST,
            depends_on=["assess-opportunities"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="executive-review",
            name="Executive Review",
            description="Review strategy report and coordinate executive presentation",
            worker_role=WorkerRole.MANAGER,
            depends_on=["strategy-report"],
        )
    )
    return plan
