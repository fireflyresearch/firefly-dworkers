"""ProjectManagementTool — abstract base for project management providers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Any

from fireflyframework_genai.tools.base import BaseTool, GuardProtocol, ParameterSpec
from pydantic import BaseModel


class ProjectTask(BaseModel):
    """Represents a task/issue from a project management provider."""

    id: str
    title: str
    description: str = ""
    status: str = ""
    assignee: str = ""
    priority: str = ""
    project: str = ""


class ProjectManagementTool(BaseTool):
    """Abstract base for project management tools.

    Subclasses must implement :meth:`_create_task`, :meth:`_list_tasks`,
    :meth:`_update_task`, and :meth:`_get_task` to provide access to a
    specific project management platform (e.g. Jira, Asana, Azure DevOps).
    """

    def __init__(self, name: str, *, description: str = "", guards: Sequence[GuardProtocol] = ()):
        super().__init__(
            name,
            description=description or f"Manage project tasks via {name}",
            tags=["project", "tasks", name],
            guards=guards,
            parameters=[
                ParameterSpec(
                    name="action",
                    type_annotation="str",
                    description="One of: create_task, list_tasks, update_task, get_task",
                    required=True,
                ),
                ParameterSpec(
                    name="title",
                    type_annotation="str",
                    description="Task title (for create)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="task_description",
                    type_annotation="str",
                    description="Task description (for create)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="task_id",
                    type_annotation="str",
                    description="Task ID (for update/get)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="status",
                    type_annotation="str",
                    description="New status (for update)",
                    required=False,
                    default="",
                ),
                ParameterSpec(
                    name="project",
                    type_annotation="str",
                    description="Project key",
                    required=False,
                    default="",
                ),
            ],
        )

    async def _execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        if action == "create_task":
            result = await self._create_task(
                kwargs.get("title", ""),
                kwargs.get("task_description", ""),
                kwargs.get("project", ""),
            )
            return result.model_dump()
        if action == "list_tasks":
            results = await self._list_tasks(kwargs.get("project", ""))
            return [t.model_dump() for t in results]
        if action == "update_task":
            result = await self._update_task(kwargs.get("task_id", ""), kwargs.get("status", ""))
            return result.model_dump()
        if action == "get_task":
            result = await self._get_task(kwargs.get("task_id", ""))
            return result.model_dump()
        raise ValueError(f"Unknown action '{action}'")

    @abstractmethod
    async def _create_task(self, title: str, description: str, project: str) -> ProjectTask: ...

    @abstractmethod
    async def _list_tasks(self, project: str) -> list[ProjectTask]: ...

    @abstractmethod
    async def _update_task(self, task_id: str, status: str) -> ProjectTask: ...

    @abstractmethod
    async def _get_task(self, task_id: str) -> ProjectTask: ...
