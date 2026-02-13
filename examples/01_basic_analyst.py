"""Basic analyst example — SWOT analysis for a consulting firm.

Demonstrates the simplest possible usage: create one AnalystWorker
and call run_sync() with a plain-text prompt.
"""

import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("Error: set the ANTHROPIC_API_KEY environment variable first.")

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.workers.analyst import AnalystWorker

config = TenantConfig(
    id="demo",
    name="Demo Corp",
    models={"default": "anthropic:claude-sonnet-4-5-20250929"},
    branding={"company_name": "Demo Corp"},
)

worker = AnalystWorker(config)
result = worker.run_sync(
    "Perform a SWOT analysis for a mid-size consulting firm "
    "expanding into AI advisory services."
)
print(result.output)
