"""Projects API router -- orchestrate multi-agent consulting projects."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from firefly_dworkers.sdk.models import ProjectEvent, ProjectRequest, ProjectResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _resolve_config(tenant_id: str):
    """Resolve tenant config, raising HTTPException on failure."""
    from firefly_dworkers.exceptions import TenantNotFoundError
    from firefly_dworkers.tenants.registry import tenant_registry

    try:
        return tenant_registry.get(tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


async def _stream_project_events(request: ProjectRequest) -> AsyncIterator[str]:
    """Generator that yields SSE events from project orchestration."""
    project_id = request.project_id or str(uuid.uuid4())

    try:
        config = await _resolve_config(request.tenant_id)
    except HTTPException as exc:
        error_event = ProjectEvent(type="error", content=exc.detail)
        yield f"data: {error_event.model_dump_json()}\n\n"
        return

    try:
        from firefly_dworkers.orchestration import ProjectOrchestrator

        orchestrator = ProjectOrchestrator(config, project_id=project_id)

        # Stream events from orchestrator
        async for event in orchestrator.run_stream(request.brief):
            yield f"data: {event.model_dump_json()}\n\n"

    except ImportError:
        # ProjectOrchestrator not yet implemented (Task 14) -- emit placeholder events
        start_event = ProjectEvent(
            type="project_start",
            content=project_id,
            metadata={"brief": request.brief[:200]},
        )
        yield f"data: {start_event.model_dump_json()}\n\n"

        complete_event = ProjectEvent(
            type="project_complete",
            content=project_id,
            metadata={"success": True, "note": "Orchestrator not yet implemented"},
        )
        yield f"data: {complete_event.model_dump_json()}\n\n"

    except Exception as exc:
        logger.exception("Project orchestration error for project '%s'", project_id)
        error_event = ProjectEvent(type="error", content=str(exc))
        yield f"data: {error_event.model_dump_json()}\n\n"


@router.post("/run")
async def run_project(request: ProjectRequest) -> StreamingResponse:
    """Run a multi-agent project with SSE streaming.

    Streams project orchestration events as Server-Sent Events.
    """
    return StreamingResponse(
        _stream_project_events(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/run/sync")
async def run_project_sync(request: ProjectRequest) -> ProjectResponse:
    """Run a multi-agent project synchronously.

    Returns the complete result in a single response.
    """
    project_id = request.project_id or str(uuid.uuid4())
    config = await _resolve_config(request.tenant_id)

    try:
        from firefly_dworkers.orchestration import ProjectOrchestrator

        orchestrator = ProjectOrchestrator(config, project_id=project_id)
        result = await orchestrator.run(request.brief)
        return ProjectResponse(
            project_id=project_id,
            success=result.get("success", True),
            deliverables=result.get("deliverables", {}),
            duration_ms=result.get("duration_ms", 0.0),
        )
    except ImportError:
        # Placeholder until Task 14 implements ProjectOrchestrator
        return ProjectResponse(
            project_id=project_id,
            success=True,
            deliverables={"note": "Orchestrator not yet implemented"},
        )
    except Exception as exc:
        logger.exception("Project orchestration error for '%s'", project_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
