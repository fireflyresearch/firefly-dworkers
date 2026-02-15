"""RemoteClient -- HTTP/SSE client for a running dworkers server."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from firefly_dworkers.sdk.models import ProjectEvent, StreamEvent
from firefly_dworkers_cli.tui.backend.models import (
    ConnectorStatus,
    ConversationSummary,
    FileAttachment,
    PlanInfo,
    UsageStats,
    WorkerInfo,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0
_STREAM_TIMEOUT = 120.0


class RemoteClient:
    """Backend that talks to a running dworkers HTTP server via REST + SSE."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._base_url = base_url.rstrip("/")

    # -- Helpers --------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    @staticmethod
    async def _parse_sse(
        response: httpx.Response,
        model_cls: type[StreamEvent] | type[ProjectEvent],
    ) -> AsyncIterator[StreamEvent | ProjectEvent]:
        """Parse an SSE stream from an httpx response.

        Reads lines starting with ``data: `` and parses JSON payloads into
        *model_cls* instances.
        """
        async for line in response.aiter_lines():
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                payload = line[6:]
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    yield model_cls.model_validate(data)
                except (json.JSONDecodeError, Exception):
                    logger.debug("Failed to parse SSE payload: %s", payload)

    # -- Workers --------------------------------------------------------------

    async def list_workers(self, tenant_id: str = "default") -> list[WorkerInfo]:
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    self._url("/api/workers"),
                    params={"tenant_id": tenant_id},
                    timeout=_DEFAULT_TIMEOUT,
                )
                resp.raise_for_status()
                return [WorkerInfo.model_validate(w) for w in resp.json()]
        except Exception:
            logger.debug("list_workers remote call failed", exc_info=True)
            return []

    async def run_worker(
        self,
        role: str,
        prompt: str,
        *,
        attachments: list[FileAttachment] | None = None,
        tenant_id: str = "default",
        conversation_id: str | None = None,
        message_history: list | None = None,
        participants: list[tuple[str, str, str]] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        import base64

        body: dict[str, Any] = {
            "worker_role": role,
            "prompt": prompt,
            "tenant_id": tenant_id,
        }
        if conversation_id:
            body["conversation_id"] = conversation_id
        if attachments:
            body["attachments"] = [
                {
                    "filename": a.filename,
                    "media_type": a.media_type,
                    "data_b64": base64.b64encode(a.data).decode(),
                }
                for a in attachments
            ]
        if participants:
            body["participants"] = [
                {"role": r, "name": n, "tagline": t} for r, n, t in participants
            ]

        try:
            async with httpx.AsyncClient() as http, http.stream(
                "POST",
                self._url("/api/workers/run"),
                json=body,
                timeout=_STREAM_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                async for event in self._parse_sse(resp, StreamEvent):
                    yield event  # type: ignore[misc]
        except Exception as exc:
            logger.warning("run_worker stream failed: %s", exc, exc_info=True)
            yield StreamEvent(type="error", content=str(exc))

    # -- Projects -------------------------------------------------------------

    async def run_project(
        self,
        brief: str,
        *,
        tenant_id: str = "default",
    ) -> AsyncIterator[ProjectEvent]:
        body: dict[str, Any] = {"brief": brief, "tenant_id": tenant_id}
        try:
            async with httpx.AsyncClient() as http, http.stream(
                "POST",
                self._url("/api/projects/run"),
                json=body,
                timeout=_STREAM_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                async for event in self._parse_sse(resp, ProjectEvent):
                    yield event  # type: ignore[misc]
        except Exception as exc:
            logger.warning("run_project stream failed: %s", exc, exc_info=True)
            yield ProjectEvent(type="error", content=str(exc))

    # -- Plans ----------------------------------------------------------------

    async def list_plans(self) -> list[PlanInfo]:
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    self._url("/api/plans"),
                    timeout=_DEFAULT_TIMEOUT,
                )
                resp.raise_for_status()
                return [PlanInfo.model_validate(p) for p in resp.json()]
        except Exception:
            logger.debug("list_plans remote call failed", exc_info=True)
            return []

    async def execute_plan(
        self,
        name: str,
        inputs: dict[str, Any] | None = None,
        *,
        tenant_id: str = "default",
    ) -> AsyncIterator[StreamEvent]:
        body: dict[str, Any] = {
            "plan_name": name,
            "tenant_id": tenant_id,
            "inputs": inputs or {},
        }
        try:
            async with httpx.AsyncClient() as http, http.stream(
                "POST",
                self._url("/api/plans/execute"),
                json=body,
                timeout=_STREAM_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                async for event in self._parse_sse(resp, StreamEvent):
                    yield event  # type: ignore[misc]
        except Exception as exc:
            logger.warning(
                "execute_plan stream failed: %s", exc, exc_info=True
            )
            yield StreamEvent(type="error", content=str(exc))

    # -- Tenants --------------------------------------------------------------

    async def list_tenants(self) -> list[str]:
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    self._url("/api/tenants"),
                    timeout=_DEFAULT_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.debug("list_tenants remote call failed", exc_info=True)
            return ["default"]

    # -- Connectors -----------------------------------------------------------

    async def list_connectors(
        self, tenant_id: str = "default"
    ) -> list[ConnectorStatus]:
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    self._url("/api/connectors"),
                    params={"tenant_id": tenant_id},
                    timeout=_DEFAULT_TIMEOUT,
                )
                resp.raise_for_status()
                return [ConnectorStatus.model_validate(c) for c in resp.json()]
        except Exception:
            logger.debug("list_connectors remote call failed", exc_info=True)
            return []

    # -- Usage ----------------------------------------------------------------

    async def get_usage_stats(self, tenant_id: str = "default") -> UsageStats:
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    self._url("/api/observability/usage"),
                    params={"tenant_id": tenant_id},
                    timeout=_DEFAULT_TIMEOUT,
                )
                resp.raise_for_status()
                return UsageStats.model_validate(resp.json())
        except Exception:
            logger.debug("get_usage_stats remote call failed", exc_info=True)
            return UsageStats()

    # -- Conversations --------------------------------------------------------

    async def list_conversations(
        self, tenant_id: str = "default"
    ) -> list[ConversationSummary]:
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    self._url("/api/conversations"),
                    params={"tenant_id": tenant_id},
                    timeout=_DEFAULT_TIMEOUT,
                )
                resp.raise_for_status()
                return [
                    ConversationSummary.model_validate(c) for c in resp.json()
                ]
        except Exception:
            logger.debug(
                "list_conversations remote call failed", exc_info=True
            )
            return []
