"""Workers API router -- list and run digital workers."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from firefly_dworkers.sdk.models import RunWorkerRequest, StreamEvent, WorkerResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def list_workers() -> list[str]:
    """List registered worker names."""
    from firefly_dworkers.workers import worker_registry

    return worker_registry.list_workers()


async def _create_worker(request: RunWorkerRequest):
    """Create a worker from the request, resolving tenant config."""
    from firefly_dworkers.exceptions import TenantNotFoundError
    from firefly_dworkers.tenants.registry import tenant_registry
    from firefly_dworkers.types import WorkerRole
    from firefly_dworkers.workers.factory import worker_factory

    try:
        config = tenant_registry.get(request.tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        role = WorkerRole(request.worker_role)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid worker role: {request.worker_role}",
        ) from exc

    kwargs: dict = {}
    if request.model:
        kwargs["model"] = request.model

    try:
        worker = worker_factory.create(role, tenant_config=config, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return worker


async def _stream_worker_events(request: RunWorkerRequest) -> AsyncIterator[str]:
    """Generator that yields SSE events from a worker execution."""
    try:
        worker = await _create_worker(request)

        stream_ctx = await worker.run_stream(
            request.prompt,
            conversation_id=request.conversation_id,
            streaming_mode="incremental",
        )
        collected_output: list[str] = []

        async with stream_ctx as stream:
            async for token in stream.stream_tokens():
                collected_output.append(token)
                event = StreamEvent(type="token", content=token)
                yield f"data: {event.model_dump_json()}\n\n"

        # Send completion event
        full_output = "".join(collected_output)
        complete_event = StreamEvent(
            type="complete",
            content=full_output,
            metadata={"worker_role": request.worker_role},
        )
        yield f"data: {complete_event.model_dump_json()}\n\n"

    except HTTPException as exc:
        logger.warning("Worker creation failed for role '%s': %s", request.worker_role, exc.detail)
        error_event = StreamEvent(
            type="error",
            content=exc.detail,
            metadata={"status_code": exc.status_code},
        )
        yield f"data: {error_event.model_dump_json()}\n\n"

    except Exception as exc:
        logger.exception("Worker streaming error for role '%s'", request.worker_role)
        error_event = StreamEvent(
            type="error",
            content=str(exc),
        )
        yield f"data: {error_event.model_dump_json()}\n\n"


@router.post("/run")
async def run_worker_stream(request: RunWorkerRequest) -> StreamingResponse:
    """Run a worker with SSE streaming.

    Streams token-by-token events as Server-Sent Events (SSE).
    """
    return StreamingResponse(
        _stream_worker_events(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/run/sync")
async def run_worker_sync(request: RunWorkerRequest) -> WorkerResponse:
    """Run a worker synchronously (non-streaming).

    Returns the complete output in a single response.
    """
    worker = await _create_worker(request)

    try:
        result = await worker.run(
            request.prompt,
            conversation_id=request.conversation_id,
        )
        output = str(result.output) if hasattr(result, "output") else str(result)
    except Exception as exc:
        logger.exception("Worker execution error for role '%s'", request.worker_role)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return WorkerResponse(
        worker_name=worker.name,
        role=request.worker_role,
        output=output,
        conversation_id=request.conversation_id,
    )
