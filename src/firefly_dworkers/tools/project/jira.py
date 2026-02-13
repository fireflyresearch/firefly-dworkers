"""JiraTool — project management via Atlassian Jira REST API.

Uses the ``atlassian-python-api`` library.  Install with::

    pip install firefly-dworkers[jira]
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import GuardProtocol

from firefly_dworkers.exceptions import ConnectorAuthError, ConnectorError
from firefly_dworkers.tools.project.base import ProjectManagementTool, ProjectTask
from firefly_dworkers.tools.registry import tool_registry

logger = logging.getLogger(__name__)

try:
    from atlassian import Jira as _Jira

    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False


@tool_registry.register("jira", category="project")
class JiraTool(ProjectManagementTool):
    """Atlassian Jira project management via the REST API.

    Configuration parameters:

    * ``base_url`` -- Jira instance URL.
    * ``username`` -- Jira username (email for Cloud).
    * ``api_token`` -- API token (Cloud) or password (Server/DC).
    * ``project_key`` -- Default project key.
    * ``cloud`` -- Whether this is a Cloud instance.
    * ``timeout`` -- HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        username: str = "",
        api_token: str = "",
        project_key: str = "",
        cloud: bool = True,
        timeout: float = 30.0,
        guards: Sequence[GuardProtocol] = (),
        **kwargs: Any,
    ):
        super().__init__(
            "jira",
            description="Manage project tasks via Atlassian Jira",
            guards=guards,
        )
        self._base_url = base_url
        self._username = username
        self._api_token = api_token
        self._project_key = project_key
        self._cloud = cloud
        self._timeout = timeout
        self._client: Any | None = None

    def _ensure_deps(self) -> None:
        if not JIRA_AVAILABLE:
            raise ImportError(
                "atlassian-python-api is required for JiraTool. "
                "Install with: pip install firefly-dworkers[jira]"
            )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        self._ensure_deps()
        if not self._base_url or not self._username or not self._api_token:
            raise ConnectorAuthError(
                "JiraTool requires base_url, username, and api_token"
            )

        self._client = _Jira(
            url=self._base_url,
            username=self._username,
            password=self._api_token,
            cloud=self._cloud,
            timeout=self._timeout,
        )
        return self._client

    def _issue_to_task(self, issue: dict[str, Any]) -> ProjectTask:
        fields = issue.get("fields", {})
        return ProjectTask(
            id=issue.get("key", ""),
            title=fields.get("summary", ""),
            description=fields.get("description", "") or "",
            status=fields.get("status", {}).get("name", ""),
            assignee=fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else "",
            priority=fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
            project=fields.get("project", {}).get("key", ""),
        )

    # -- port implementation -------------------------------------------------

    async def _create_task(self, title: str, description: str, project: str) -> ProjectTask:
        client = self._get_client()
        project_key = project or self._project_key
        if not project_key:
            raise ConnectorError("JiraTool create_task requires a project key")

        fields = {
            "project": {"key": project_key},
            "summary": title,
            "description": description,
            "issuetype": {"name": "Task"},
        }
        result = await asyncio.to_thread(client.create_issue, fields=fields)
        issue_key = result.get("key", "") if isinstance(result, dict) else str(result)
        issue = await asyncio.to_thread(client.issue, issue_key)
        return self._issue_to_task(issue)

    async def _list_tasks(self, project: str) -> list[ProjectTask]:
        client = self._get_client()
        project_key = project or self._project_key
        jql = f"project = {project_key} ORDER BY updated DESC" if project_key else "ORDER BY updated DESC"

        results = await asyncio.to_thread(
            client.jql, jql, limit=50
        )
        return [
            self._issue_to_task(issue)
            for issue in results.get("issues", [])
        ]

    async def _update_task(self, task_id: str, status: str) -> ProjectTask:
        client = self._get_client()
        if not task_id:
            raise ConnectorError("JiraTool update_task requires task_id")

        if status:
            # Get available transitions
            transitions = await asyncio.to_thread(client.get_issue_transitions, task_id)
            target = None
            for t in transitions:
                if t.get("name", "").lower() == status.lower() or t.get("to", {}).get("name", "").lower() == status.lower():
                    target = t["id"]
                    break
            if target:
                await asyncio.to_thread(client.set_issue_status, task_id, status)
            else:
                logger.warning("Transition to '%s' not found for %s", status, task_id)

        issue = await asyncio.to_thread(client.issue, task_id)
        return self._issue_to_task(issue)

    async def _get_task(self, task_id: str) -> ProjectTask:
        client = self._get_client()
        if not task_id:
            raise ConnectorError("JiraTool get_task requires task_id")

        issue = await asyncio.to_thread(client.issue, task_id)
        return self._issue_to_task(issue)
