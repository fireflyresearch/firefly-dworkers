"""Plans API router -- list, inspect, and execute consulting plans."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from firefly_dworkers.exceptions import PlanNotFoundError
from firefly_dworkers.sdk.models import ExecutePlanRequest, PlanResponse

router = APIRouter()


@router.get("")
async def list_plans() -> list[str]:
    """List available plan templates."""
    from firefly_dworkers.plans import plan_registry

    return plan_registry.list_plans()


@router.get("/{plan_name}")
async def get_plan(plan_name: str) -> dict:
    """Get plan details by name."""
    from firefly_dworkers.plans import plan_registry

    try:
        plan = plan_registry.get(plan_name)
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "name": plan.name,
        "description": plan.description,
        "steps": [s.model_dump() for s in plan.steps],
    }


@router.post("/execute")
async def execute_plan(request: ExecutePlanRequest) -> PlanResponse:
    """Execute a consulting plan.

    Returns a placeholder response -- real execution requires LLM integration.
    """
    from firefly_dworkers.plans import plan_registry

    try:
        plan_registry.get(request.plan_name)
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return PlanResponse(
        plan_name=request.plan_name,
        success=True,
        outputs={"status": "placeholder", "inputs": request.inputs},
        duration_ms=0.0,
    )
