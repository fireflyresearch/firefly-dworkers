"""Pre-built consulting plan templates.

Importing this module registers all built-in plan templates into the
:data:`~firefly_dworkers.plans.registry.plan_registry`.
"""

from __future__ import annotations

from firefly_dworkers.plans.registry import plan_registry
from firefly_dworkers.plans.templates.customer_segmentation import customer_segmentation_plan
from firefly_dworkers.plans.templates.market_analysis import market_analysis_plan
from firefly_dworkers.plans.templates.process_improvement import process_improvement_plan
from firefly_dworkers.plans.templates.technology_assessment import technology_assessment_plan

_TEMPLATES = [
    customer_segmentation_plan(),
    market_analysis_plan(),
    process_improvement_plan(),
    technology_assessment_plan(),
]

for _plan in _TEMPLATES:
    plan_registry.register(_plan)
