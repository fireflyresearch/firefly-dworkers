"""Plans API router -- list, inspect, and execute consulting plans."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from firefly_dworkers.exceptions import PlanNotFoundError
from firefly_dworkers.sdk.models import ExecutePlanRequest, PlanResponse, StreamEvent

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# SSE event handler -- bridges PipelineEventHandler to an asyncio.Queue
# ---------------------------------------------------------------------------


class _SSEEventHandler:
    """PipelineEventHandler that pushes StreamEvent instances to a queue."""

    def __init__(self, queue: asyncio.Queue[StreamEvent | None]) -> None:
        self._queue = queue

    async def on_node_start(self, node_id: str, pipeline_name: str) -> None:
        await self._queue.put(
            StreamEvent(
                type="node_start",
                content=node_id,
                metadata={"pipeline": pipeline_name},
            )
        )

    async def on_node_complete(self, node_id: str, pipeline_name: str, latency_ms: float) -> None:
        await self._queue.put(
            StreamEvent(
                type="node_complete",
                content=node_id,
                metadata={"pipeline": pipeline_name, "latency_ms": latency_ms},
            )
        )

    async def on_node_error(self, node_id: str, pipeline_name: str, error: str) -> None:
        await self._queue.put(
            StreamEvent(
                type="node_error",
                content=error,
                metadata={"pipeline": pipeline_name, "node_id": node_id},
            )
        )

    async def on_node_skip(self, node_id: str, pipeline_name: str, reason: str) -> None:
        await self._queue.put(
            StreamEvent(
                type="node_skip",
                content=reason,
                metadata={"pipeline": pipeline_name, "node_id": node_id},
            )
        )

    async def on_pipeline_complete(self, pipeline_name: str, success: bool, duration_ms: float) -> None:
        await self._queue.put(
            StreamEvent(
                type="pipeline_complete",
                content=pipeline_name,
                metadata={"success": success, "duration_ms": duration_ms},
            )
        )
        # Signal end of stream
        await self._queue.put(None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _build_and_run_pipeline(
    request: ExecutePlanRequest,
    queue: asyncio.Queue[StreamEvent | None],
) -> None:
    """Build a pipeline from the plan + tenant config and run it.

    Progress events are pushed to *queue* via the SSE event handler.
    """
    from firefly_dworkers.exceptions import TenantNotFoundError
    from firefly_dworkers.plans import plan_registry
    from firefly_dworkers.plans.builder import PlanBuilder
    from firefly_dworkers.tenants.registry import tenant_registry

    try:
        plan = plan_registry.get(request.plan_name)
    except PlanNotFoundError:
        await queue.put(StreamEvent(type="error", content=f"Plan '{request.plan_name}' not found"))
        await queue.put(None)
        return

    try:
        config = tenant_registry.get(request.tenant_id)
    except TenantNotFoundError:
        await queue.put(StreamEvent(type="error", content=f"Tenant '{request.tenant_id}' not found"))
        await queue.put(None)
        return

    handler = _SSEEventHandler(queue)
    try:
        pipeline = PlanBuilder(plan, config).build()
        # Inject the event handler after build() returns
        pipeline._event_handler = handler
        await pipeline.run(inputs=request.inputs)
    except Exception as exc:
        logger.exception("Plan execution error for '%s'", request.plan_name)
        await queue.put(StreamEvent(type="error", content=str(exc)))
        await queue.put(None)


async def _stream_plan_events(request: ExecutePlanRequest) -> AsyncIterator[str]:
    """Async generator that yields SSE-formatted events from plan execution."""
    queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()

    # Start pipeline execution in a background task
    task = asyncio.create_task(_build_and_run_pipeline(request, queue))

    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {event.model_dump_json()}\n\n"
    finally:
        if not task.done():
            task.cancel()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/execute")
async def execute_plan(request: ExecutePlanRequest) -> StreamingResponse:
    """Execute a consulting plan with SSE streaming.

    Streams pipeline progress events (node_start, node_complete, etc.)
    as Server-Sent Events.
    """
    return StreamingResponse(
        _stream_plan_events(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/execute/sync")
async def execute_plan_sync(request: ExecutePlanRequest) -> PlanResponse:
    """Execute a consulting plan synchronously.

    Returns the complete result in a single response.
    """
    from firefly_dworkers.exceptions import TenantNotFoundError
    from firefly_dworkers.plans import plan_registry
    from firefly_dworkers.plans.builder import PlanBuilder
    from firefly_dworkers.tenants.registry import tenant_registry

    try:
        plan = plan_registry.get(request.plan_name)
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        config = tenant_registry.get(request.tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        pipeline = PlanBuilder(plan, config).build()
        result = await pipeline.run(inputs=request.inputs)
    except Exception as exc:
        logger.exception("Plan execution error for '%s'", request.plan_name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PlanResponse(
        plan_name=request.plan_name,
        success=result.success,
        outputs={nid: nr.output for nid, nr in result.outputs.items() if nr.success},
        duration_ms=result.total_duration_ms,
    )
