"""Tests for ProjectManagementTool abstract base."""

from __future__ import annotations

import pytest

from firefly_dworkers.tools.project.base import ProjectManagementTool, ProjectTask


class FakeProjectTool(ProjectManagementTool):
    """Concrete implementation for testing."""

    async def _create_task(self, title: str, description: str, project: str) -> ProjectTask:
        return ProjectTask(
            id="task-1",
            title=title,
            description=description,
            status="todo",
            assignee="",
            priority="medium",
            project=project,
        )

    async def _list_tasks(self, project: str) -> list[ProjectTask]:
        return [
            ProjectTask(id="task-1", title="First task", status="todo", project=project),
            ProjectTask(id="task-2", title="Second task", status="in_progress", project=project),
        ]

    async def _update_task(self, task_id: str, status: str) -> ProjectTask:
        return ProjectTask(
            id=task_id,
            title="Updated task",
            status=status,
        )

    async def _get_task(self, task_id: str) -> ProjectTask:
        return ProjectTask(
            id=task_id,
            title="Retrieved task",
            description="Task details",
            status="in_progress",
            assignee="alice",
            priority="high",
            project="PROJ",
        )


class TestProjectManagementTool:
    async def test_create_task_action(self):
        tool = FakeProjectTool("test_pm")
        result = await tool.execute(
            action="create_task",
            title="New feature",
            task_description="Build the thing",
            project="PROJ",
        )
        assert result["id"] == "task-1"
        assert result["title"] == "New feature"
        assert result["description"] == "Build the thing"
        assert result["status"] == "todo"
        assert result["project"] == "PROJ"

    async def test_list_tasks_action(self):
        tool = FakeProjectTool("test_pm")
        result = await tool.execute(action="list_tasks", project="PROJ")
        assert len(result) == 2
        assert result[0]["title"] == "First task"
        assert result[1]["status"] == "in_progress"

    async def test_update_task_action(self):
        tool = FakeProjectTool("test_pm")
        result = await tool.execute(action="update_task", task_id="task-1", status="done")
        assert result["id"] == "task-1"
        assert result["status"] == "done"

    async def test_get_task_action(self):
        tool = FakeProjectTool("test_pm")
        result = await tool.execute(action="get_task", task_id="task-1")
        assert result["id"] == "task-1"
        assert result["title"] == "Retrieved task"
        assert result["assignee"] == "alice"
        assert result["priority"] == "high"

    async def test_unknown_action_raises(self):
        tool = FakeProjectTool("test_pm")
        with pytest.raises(Exception, match="Unknown action"):
            await tool.execute(action="archive")

    def test_name(self):
        tool = FakeProjectTool("jira")
        assert tool.name == "jira"

    def test_tags(self):
        tool = FakeProjectTool("jira")
        assert "project" in tool.tags
        assert "tasks" in tool.tags
        assert "jira" in tool.tags

    def test_description_default(self):
        tool = FakeProjectTool("jira")
        assert "jira" in tool.description

    def test_description_custom(self):
        tool = FakeProjectTool("jira", description="Jira project management")
        assert tool.description == "Jira project management"

    def test_parameters(self):
        tool = FakeProjectTool("test_pm")
        param_names = [p.name for p in tool.parameters]
        assert "action" in param_names
        assert "title" in param_names
        assert "task_description" in param_names
        assert "task_id" in param_names
        assert "status" in param_names
        assert "project" in param_names

    def test_is_base_tool(self):
        from fireflyframework_genai.tools.base import BaseTool

        assert isinstance(FakeProjectTool("test"), BaseTool)
