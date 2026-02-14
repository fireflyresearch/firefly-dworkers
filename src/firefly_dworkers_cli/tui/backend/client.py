"""DworkersClient protocol and auto-detect factory."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from firefly_dworkers.sdk.models import ProjectEvent, StreamEvent
from firefly_dworkers_cli.tui.backend.models import (
    ConnectorStatus,
    ConversationSummary,
    PlanInfo,
    UsageStats,
    WorkerInfo,
)

# Re-export for convenience so downstream code can import from client.
__all__ = [
    "DworkersClient",
    "ProjectEvent",
    "StreamEvent",
    "create_client",
]


@runtime_checkable
class DworkersClient(Protocol):
    """Protocol for TUI backend -- implemented by LocalClient and RemoteClient."""

    async def list_workers(self, tenant_id: str = "default") -> list[WorkerInfo]: ...

    async def run_worker(
        self,
        role: str,
        prompt: str,
        *,
        tenant_id: str = "default",
        conversation_id: str | None = None,
    ) -> AsyncIterator[StreamEvent]: ...

    async def run_project(
        self,
        brief: str,
        *,
        tenant_id: str = "default",
    ) -> AsyncIterator[ProjectEvent]: ...

    async def list_plans(self) -> list[PlanInfo]: ...

    async def execute_plan(
        self,
        name: str,
        inputs: dict[str, Any] | None = None,
        *,
        tenant_id: str = "default",
    ) -> AsyncIterator[StreamEvent]: ...

    async def list_tenants(self) -> list[str]: ...

    async def list_connectors(
        self, tenant_id: str = "default"
    ) -> list[ConnectorStatus]: ...

    async def get_usage_stats(self, tenant_id: str = "default") -> UsageStats: ...

    async def list_conversations(
        self, tenant_id: str = "default"
    ) -> list[ConversationSummary]: ...


async def create_client(
    *,
    mode: str = "auto",
    server_url: str | None = None,
    checkpoint_handler: Any | None = None,
) -> DworkersClient:
    """Create a backend client.

    Parameters
    ----------
    mode:
        ``"auto"`` (default) -- try the remote server first, fall back to
        local.  ``"local"`` -- skip the server probe and return a
        :class:`LocalClient` immediately.  ``"remote"`` -- require a
        reachable server; raise :class:`ConnectionError` if the health
        endpoint is unreachable.
    server_url:
        Override for the ``DWORKERS_SERVER_URL`` environment variable.  When
        *None* the env-var is read (default ``http://localhost:8000``).
    checkpoint_handler:
        Optional :class:`TUICheckpointHandler` passed through to
        :class:`LocalClient` so workers can raise checkpoints.
    """
    if mode == "local":
        from firefly_dworkers_cli.tui.backend.local import LocalClient

        return LocalClient(checkpoint_handler=checkpoint_handler)

    resolved_url = server_url or os.environ.get(
        "DWORKERS_SERVER_URL", "http://localhost:8000"
    )

    try:
        import httpx

        async with httpx.AsyncClient() as http:
            resp = await http.get(f"{resolved_url}/health", timeout=1.0)
            if resp.status_code == 200:
                from firefly_dworkers_cli.tui.backend.remote import RemoteClient

                return RemoteClient(base_url=resolved_url)
    except Exception:
        if mode == "remote":
            raise ConnectionError(
                f"Cannot reach dworkers server at {resolved_url}"
            )

    if mode == "remote":
        # Server responded but with a non-200 status.
        raise ConnectionError(
            f"Cannot reach dworkers server at {resolved_url}"
        )

    # mode == "auto" -- fall back to local
    from firefly_dworkers_cli.tui.backend.local import LocalClient

    return LocalClient(checkpoint_handler=checkpoint_handler)
