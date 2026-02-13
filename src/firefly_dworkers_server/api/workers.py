"""Workers API router -- list and run digital workers."""

from __future__ import annotations

from fastapi import APIRouter

from firefly_dworkers.sdk.models import RunWorkerRequest, WorkerResponse

router = APIRouter()


@router.get("")
async def list_workers() -> list[str]:
    """List registered worker names."""
    from firefly_dworkers.workers import worker_registry

    return worker_registry.list_workers()


@router.post("/run")
async def run_worker(request: RunWorkerRequest) -> WorkerResponse:
    """Run a worker with the given prompt.

    Creates a worker for the specified role and returns a placeholder response.
    Real LLM execution is not performed in this MVP endpoint.
    """
    return WorkerResponse(
        worker_name=f"{request.worker_role}-worker",
        role=request.worker_role,
        output=f"[placeholder] Processed prompt: {request.prompt[:100]}",
        conversation_id=request.conversation_id,
    )
