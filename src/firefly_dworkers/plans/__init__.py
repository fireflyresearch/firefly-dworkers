"""Plans layer -- multi-step consulting workflow DAGs.

Plans define reusable pipeline templates where nodes represent worker tasks.
They wrap the framework's :class:`PipelineBuilder` to create pre-configured
workflows for common consulting projects.
"""

from __future__ import annotations

# Import templates to trigger registration
import firefly_dworkers.plans.templates  # noqa: F401
from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.plans.builder import PlanBuilder
from firefly_dworkers.plans.registry import PlanRegistry, plan_registry

__all__ = ["BasePlan", "PlanStep", "PlanRegistry", "plan_registry", "PlanBuilder"]
