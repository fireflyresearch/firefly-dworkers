"""Research brief example — market trends investigation.

Uses a ResearcherWorker to produce a structured research brief.
The researcher toolkit includes consulting tools (report generation,
RSS feed analysis) that work without external service credentials.
"""

import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("Error: set the ANTHROPIC_API_KEY environment variable first.")

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.workers.researcher import ResearcherWorker

config = TenantConfig(
    id="demo",
    name="Demo Corp",
    models={"default": "anthropic:claude-sonnet-4-5-20250929"},
    branding={"company_name": "Demo Corp"},
)

worker = ResearcherWorker(config)
result = worker.run_sync(
    "Using your existing knowledge, produce a structured research "
    "brief on the adoption of generative AI in management consulting. "
    "Cover current adoption rates, key use cases, competitive "
    "landscape, and projected growth over the next 3 years. "
    "Use the report_generation tool to format your findings."
)
print(result.output)
