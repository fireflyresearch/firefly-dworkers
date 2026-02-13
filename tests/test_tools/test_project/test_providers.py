"""Tests for concrete project management providers (Jira, Asana).

These tests mock external API calls to validate configuration, error handling,
and business logic without requiring real credentials or network access.

NOTE: ``BaseTool.execute()`` wraps all exceptions in ``ToolError``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.project.asana import AsanaTool
from firefly_dworkers.tools.project.jira import JiraTool

# ---------------------------------------------------------------------------
# JiraTool
# ---------------------------------------------------------------------------


class TestJiraTool:
    def test_instantiation(self):
        tool = JiraTool()
        assert tool is not None

    def test_name(self):
        assert JiraTool().name == "jira"

    def test_tags(self):
        tags = JiraTool().tags
        assert "project" in tags
        assert "jira" in tags

    def test_is_base_tool(self):
        assert isinstance(JiraTool(), BaseTool)

    def test_config_params(self):
        tool = JiraTool(
            base_url="https://jira.example.com",
            username="admin",
            api_token="tok",
            project_key="PROJ",
            cloud=False,
            timeout=60.0,
        )
        assert tool._base_url == "https://jira.example.com"
        assert tool._username == "admin"
        assert tool._api_token == "tok"
        assert tool._project_key == "PROJ"
        assert tool._cloud is False
        assert tool._timeout == 60.0

    async def test_auth_error_when_missing_credentials(self):
        tool = JiraTool()
        tool._ensure_deps = MagicMock()  # bypass dep check
        with pytest.raises(ToolError, match="base_url|username|api_token"):
            await tool.execute(action="list_tasks", project="PROJ")

    async def test_create_task_with_mocked_client(self):
        tool = JiraTool(base_url="https://jira.example.com", username="u", api_token="t", project_key="PROJ")
        mock_client = MagicMock()
        mock_client.create_issue.return_value = {"key": "PROJ-1"}
        mock_client.issue.return_value = {
            "key": "PROJ-1",
            "fields": {
                "summary": "Fix bug",
                "description": "Fix login bug",
                "status": {"name": "To Do"},
                "assignee": None,
                "priority": {"name": "Medium"},
                "project": {"key": "PROJ"},
            },
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="create_task", title="Fix bug", task_description="Fix login bug", project="PROJ")
        assert result["id"] == "PROJ-1"
        assert result["title"] == "Fix bug"
        assert result["status"] == "To Do"
        assert result["project"] == "PROJ"

    async def test_list_tasks_with_mocked_client(self):
        tool = JiraTool(base_url="https://jira.example.com", username="u", api_token="t", project_key="PROJ")
        mock_client = MagicMock()
        mock_client.jql.return_value = {
            "issues": [
                {
                    "key": "PROJ-1",
                    "fields": {
                        "summary": "Task One",
                        "description": "Description",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "Alice"},
                        "priority": {"name": "High"},
                        "project": {"key": "PROJ"},
                    },
                },
                {
                    "key": "PROJ-2",
                    "fields": {
                        "summary": "Task Two",
                        "description": "Another task",
                        "status": {"name": "Done"},
                        "assignee": None,
                        "priority": None,
                        "project": {"key": "PROJ"},
                    },
                },
            ]
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="list_tasks", project="PROJ")
        assert len(result) == 2
        assert result[0]["id"] == "PROJ-1"
        assert result[0]["assignee"] == "Alice"
        assert result[1]["status"] == "Done"

    async def test_update_task_with_mocked_client(self):
        tool = JiraTool(base_url="https://jira.example.com", username="u", api_token="t")
        mock_client = MagicMock()
        mock_client.get_issue_transitions.return_value = [
            {"id": "31", "name": "Done", "to": {"name": "Done"}},
        ]
        mock_client.set_issue_status.return_value = None
        mock_client.issue.return_value = {
            "key": "PROJ-123",
            "fields": {
                "summary": "Updated task",
                "description": "desc",
                "status": {"name": "Done"},
                "assignee": None,
                "priority": None,
                "project": {"key": "PROJ"},
            },
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="update_task", task_id="PROJ-123", status="Done")
        assert result["id"] == "PROJ-123"
        assert result["status"] == "Done"

    async def test_get_task_with_mocked_client(self):
        tool = JiraTool(base_url="https://jira.example.com", username="u", api_token="t")
        mock_client = MagicMock()
        mock_client.issue.return_value = {
            "key": "PROJ-456",
            "fields": {
                "summary": "My Task",
                "description": "Details here",
                "status": {"name": "Open"},
                "assignee": {"displayName": "Bob"},
                "priority": {"name": "Low"},
                "project": {"key": "PROJ"},
            },
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="get_task", task_id="PROJ-456")
        assert result["id"] == "PROJ-456"
        assert result["title"] == "My Task"
        assert result["description"] == "Details here"
        assert result["assignee"] == "Bob"

    async def test_get_task_requires_task_id(self):
        tool = JiraTool(base_url="https://jira.example.com", username="u", api_token="t")
        mock_client = MagicMock()
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        with pytest.raises(ToolError, match="task_id"):
            await tool.execute(action="get_task", task_id="")


# ---------------------------------------------------------------------------
# AsanaTool
# ---------------------------------------------------------------------------


class TestAsanaTool:
    def test_instantiation(self):
        tool = AsanaTool()
        assert tool is not None

    def test_name(self):
        assert AsanaTool().name == "asana"

    def test_tags(self):
        tags = AsanaTool().tags
        assert "project" in tags
        assert "asana" in tags

    def test_is_base_tool(self):
        assert isinstance(AsanaTool(), BaseTool)

    def test_config_params(self):
        tool = AsanaTool(access_token="pat-token", workspace_gid="12345", timeout=45.0)
        assert tool._access_token == "pat-token"
        assert tool._workspace_gid == "12345"
        assert tool._timeout == 45.0

    async def test_auth_error_when_missing_token(self):
        tool = AsanaTool()
        tool._ensure_deps = MagicMock()  # bypass dep check
        with pytest.raises(ToolError, match="access_token"):
            await tool.execute(action="get_task", task_id="task-1")

    async def test_create_task_with_mocked_api(self):
        tool = AsanaTool(access_token="pat-test", workspace_gid="ws-1")
        tool._api_post = AsyncMock(return_value={  # type: ignore[method-assign]
            "data": {
                "gid": "task-new",
                "name": "Design review",
                "notes": "Review mockups",
                "assignee": None,
                "projects": [{"name": "design"}],
            }
        })
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="create_task", title="Design review", task_description="Review mockups", project="proj-1")
        assert result["id"] == "task-new"
        assert result["title"] == "Design review"
        assert result["project"] == "design"

    async def test_list_tasks_requires_project_or_workspace(self):
        tool = AsanaTool(access_token="pat-test")
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="project GID or workspace_gid"):
            await tool.execute(action="list_tasks", project="")

    async def test_list_tasks_with_mocked_api(self):
        tool = AsanaTool(access_token="pat-test", workspace_gid="ws-1")
        tool._api_get = AsyncMock(return_value={  # type: ignore[method-assign]
            "data": [
                {
                    "gid": "task-1",
                    "name": "Task A",
                    "notes": "Do thing A",
                    "assignee": {"name": "Alice"},
                    "projects": [{"name": "marketing"}],
                },
                {
                    "gid": "task-2",
                    "name": "Task B",
                    "notes": "Do thing B",
                    "assignee": None,
                    "projects": [],
                },
            ]
        })
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="list_tasks", project="proj-1")
        assert len(result) == 2
        assert result[0]["title"] == "Task A"
        assert result[0]["assignee"] == "Alice"
        assert result[1]["assignee"] == ""

    async def test_update_task_completes(self):
        tool = AsanaTool(access_token="pat-test")
        tool._api_put = AsyncMock(return_value={  # type: ignore[method-assign]
            "data": {
                "gid": "task-789",
                "name": "Updated task",
                "notes": "",
                "completed_at": "2025-01-01T00:00:00Z",
                "assignee": None,
                "projects": [],
            }
        })
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="update_task", task_id="task-789", status="completed")
        assert result["id"] == "task-789"

    async def test_update_task_requires_task_id(self):
        tool = AsanaTool(access_token="pat-test")
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="task_id"):
            await tool.execute(action="update_task", task_id="", status="done")

    async def test_get_task_with_mocked_api(self):
        tool = AsanaTool(access_token="pat-test")
        tool._api_get = AsyncMock(return_value={  # type: ignore[method-assign]
            "data": {
                "gid": "task-abc",
                "name": "My Task",
                "notes": "Details",
                "assignee": {"name": "Bob"},
                "projects": [{"name": "eng"}],
            }
        })
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="get_task", task_id="task-abc")
        assert result["id"] == "task-abc"
        assert result["title"] == "My Task"
        assert result["assignee"] == "Bob"

    async def test_get_task_requires_task_id(self):
        tool = AsanaTool(access_token="pat-test")
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="task_id"):
            await tool.execute(action="get_task", task_id="")
