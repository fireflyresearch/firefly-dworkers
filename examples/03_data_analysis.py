"""Data analysis example — analyze an inline CSV dataset.

Uses a DataAnalystWorker to extract insights from tabular data
embedded directly in the prompt.
"""

import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("Error: set the ANTHROPIC_API_KEY environment variable first.")

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.workers.data_analyst import DataAnalystWorker

config = TenantConfig(
    id="demo",
    name="Demo Corp",
    models={"default": "anthropic:claude-sonnet-4-5-20250929"},
    branding={"company_name": "Demo Corp"},
)

SAMPLE_CSV = """\
quarter,revenue_usd,new_clients,churn_rate,avg_project_value_usd
Q1-2024,1200000,18,0.05,66667
Q2-2024,1350000,22,0.04,61364
Q3-2024,1100000,15,0.08,73333
Q4-2024,1500000,25,0.03,60000
Q1-2025,1450000,20,0.06,72500
Q2-2025,1600000,28,0.03,57143
"""

worker = DataAnalystWorker(config)
result = worker.run_sync(
    f"Analyse the following quarterly performance data for a consulting "
    f"firm and identify key trends, anomalies, and actionable recommendations.\n\n"
    f"```csv\n{SAMPLE_CSV}```"
)
print(result.output)
