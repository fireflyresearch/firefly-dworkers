"""AsanaTool — project management via Asana REST API.

Uses ``httpx`` for async HTTP requests against the Asana API.  Install with::

    pip install httpx
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError
from firefly_dworkers.tools.project.base import ProjectManagementTool, ProjectTask
from firefly_dworkers.tools.registry import tool_registry

logger = logging.getLogger(__name__)

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    HTTPX_AVAILABLE = False

_ASANA_BASE = "https://app.asana.com/api/1.0"


@tool_registry.register("asana", category="project")
class AsanaTool(ProjectManagementTool):
    """Asana project management via the REST API.

    Configuration parameters:

    * ``access_token`` -- Asana Personal Access Token.
    * ``workspace_gid`` -- Default workspace GID.
    * ``timeout`` -- HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        access_token: str = "",
        workspace_gid: str = "",
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__(
            "asana",
            description="Manage project tasks via Asana",
            guards=guards,
        )
        self._access_token = access_token
        self._workspace_gid = workspace_gid
        self._timeout = timeout

    def _ensure_deps(self) -> None:
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for AsanaTool. Install with: pip install httpx"
            )

    def _headers(self) -> dict[str, str]:
        if not self._access_token:
            raise ConnectorAuthError("AsanaTool requires access_token")
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    async def _api_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_deps()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{_ASANA_BASE}{path}",
                headers=self._headers(),
                params=params or {},
            )
            if resp.status_code == 401:
                raise ConnectorAuthError("Asana token invalid or expired")
            resp.raise_for_status()
            return resp.json()

    async def _api_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        self._ensure_deps()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{_ASANA_BASE}{path}",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"data": body},
            )
            if resp.status_code == 401:
                raise ConnectorAuthError("Asana token invalid or expired")
            resp.raise_for_status()
            return resp.json()

    async def _api_put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        self._ensure_deps()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.put(
                f"{_ASANA_BASE}{path}",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"data": body},
            )
            resp.raise_for_status()
            return resp.json()

    def _to_task(self, data: dict[str, Any]) -> ProjectTask:
        return ProjectTask(
            id=data.get("gid", ""),
            title=data.get("name", ""),
            description=data.get("notes", ""),
            status=data.get("assignee_status", data.get("completed_at") and "completed" or "incomplete"),
            assignee=data.get("assignee", {}).get("name", "") if data.get("assignee") else "",
            project=data.get("projects", [{}])[0].get("name", "") if data.get("projects") else "",
        )

    # -- port implementation -------------------------------------------------

    async def _create_task(self, title: str, description: str, project: str) -> ProjectTask:
        body: dict[str, Any] = {
            "name": title,
            "notes": description,
        }
        if self._workspace_gid:
            body["workspace"] = self._workspace_gid
        if project:
            body["projects"] = [project]

        result = await self._api_post("/tasks", body)
        return self._to_task(result.get("data", {}))

    async def _list_tasks(self, project: str) -> list[ProjectTask]:
        if project:
            data = await self._api_get(
                f"/projects/{project}/tasks",
                params={"opt_fields": "name,notes,assignee.name,assignee_status,completed_at,projects.name"},
            )
        elif self._workspace_gid:
            data = await self._api_get(
                "/tasks",
                params={
                    "workspace": self._workspace_gid,
                    "opt_fields": "name,notes,assignee.name,assignee_status,completed_at,projects.name",
                    "limit": 50,
                },
            )
        else:
            raise ConnectorError("AsanaTool list_tasks requires project GID or workspace_gid")

        return [self._to_task(t) for t in data.get("data", [])]

    async def _update_task(self, task_id: str, status: str) -> ProjectTask:
        if not task_id:
            raise ConnectorError("AsanaTool update_task requires task_id")

        body: dict[str, Any] = {}
        if status.lower() in {"completed", "complete", "done"}:
            body["completed"] = True
        elif status:
            body["completed"] = False

        result = await self._api_put(f"/tasks/{task_id}", body)
        return self._to_task(result.get("data", {}))

    async def _get_task(self, task_id: str) -> ProjectTask:
        if not task_id:
            raise ConnectorError("AsanaTool get_task requires task_id")

        data = await self._api_get(
            f"/tasks/{task_id}",
            params={"opt_fields": "name,notes,assignee.name,assignee_status,completed_at,projects.name"},
        )
        return self._to_task(data.get("data", {}))
