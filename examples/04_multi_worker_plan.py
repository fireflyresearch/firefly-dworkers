"""Multi-worker plan execution — process improvement engagement.

Executes the built-in ``process-improvement`` plan template.  The plan
creates a DAG of workers (Analyst, Researcher, DataAnalyst, Manager) that
run steps in dependency order — parallel where possible.

DAG structure::

    map-current-processes (analyst)
        |                  |
    research-best-practices (researcher)   analyze-process-data (data analyst)
        |                  |
    identify-improvements (analyst)
        |
    improvement-report (analyst)
        |
    stakeholder-review (manager)
"""

import asyncio
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("Error: set the ANTHROPIC_API_KEY environment variable first.")

from firefly_dworkers.plans import PlanBuilder, plan_registry
from firefly_dworkers.tenants.config import TenantConfig

config = TenantConfig(
    id="demo",
    name="Demo Corp",
    models={"default": "anthropic:claude-sonnet-4-5-20250929"},
    branding={"company_name": "Demo Corp"},
)


async def main() -> None:
    plan = plan_registry.get("process-improvement")
    pipeline = PlanBuilder(plan, config).build()
    result = await pipeline.run(inputs={"target_process": "Client onboarding"})

    print(f"Pipeline succeeded: {result.success}")
    print(f"Duration: {result.total_duration_ms:.0f} ms\n")

    for node_id, node_result in result.outputs.items():
        status = "ok" if node_result.success else "FAILED"
        print(f"  [{status}] {node_id}")

    print(f"\n--- Final Output ---\n{result.final_output}")


asyncio.run(main())
