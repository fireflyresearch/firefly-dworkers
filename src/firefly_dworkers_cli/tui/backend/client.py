"""DworkersClient protocol and auto-detect factory."""

from __future__ import annotations

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


async def create_client() -> DworkersClient:
    """Auto-detect: try remote server first, fall back to local."""
    try:
        import httpx

        async with httpx.AsyncClient() as http:
            resp = await http.get("http://localhost:8000/health", timeout=1.0)
            if resp.status_code == 200:
                from firefly_dworkers_cli.tui.backend.remote import RemoteClient

                return RemoteClient(base_url="http://localhost:8000")
    except Exception:
        pass

    from firefly_dworkers_cli.tui.backend.local import LocalClient

    return LocalClient()
