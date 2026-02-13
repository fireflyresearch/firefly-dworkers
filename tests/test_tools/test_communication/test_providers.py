"""Tests for concrete communication providers (Email, Slack, Teams).

These tests mock external API calls to validate configuration, error handling,
and business logic without requiring real credentials or network access.

NOTE: ``BaseTool.execute()`` wraps all exceptions in ``ToolError``, so tests
that exercise ``execute()`` must catch ``ToolError``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fireflyframework_genai.exceptions import ToolError
from fireflyframework_genai.tools.base import BaseTool

from firefly_dworkers.tools.communication.email import EmailTool
from firefly_dworkers.tools.communication.slack import SlackTool
from firefly_dworkers.tools.communication.teams import TeamsTool

# ---------------------------------------------------------------------------
# EmailTool
# ---------------------------------------------------------------------------


class TestEmailTool:
    def test_instantiation(self):
        tool = EmailTool()
        assert tool is not None

    def test_name(self):
        assert EmailTool().name == "email"

    def test_tags(self):
        tags = EmailTool().tags
        assert "communication" in tags
        assert "email" in tags

    def test_is_base_tool(self):
        assert isinstance(EmailTool(), BaseTool)

    def test_config_params(self):
        tool = EmailTool(
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_use_tls=False,
            imap_host="imap.example.com",
            imap_port=143,
            username="user@example.com",
            password="pass",
            from_address="noreply@example.com",
            timeout=60.0,
        )
        assert tool._smtp_host == "smtp.example.com"
        assert tool._smtp_port == 465
        assert tool._smtp_use_tls is False
        assert tool._imap_host == "imap.example.com"
        assert tool._imap_port == 143
        assert tool._username == "user@example.com"
        assert tool._from_address == "noreply@example.com"
        assert tool._timeout == 60.0

    def test_from_address_defaults_to_username(self):
        tool = EmailTool(username="user@example.com")
        assert tool._from_address == "user@example.com"

    async def test_send_requires_smtp_host(self):
        """Without smtp_host, send fails (but may hit dep check first)."""
        tool = EmailTool(username="u", password="p")
        with pytest.raises(ToolError, match="smtp_host|aiosmtplib"):
            await tool.execute(action="send", channel="to@example.com", content="Hello!")

    async def test_send_requires_credentials(self):
        tool = EmailTool(smtp_host="smtp.example.com")
        with pytest.raises(ToolError, match="username|aiosmtplib"):
            await tool.execute(action="send", channel="to@example.com", content="Hello!")

    async def test_send_with_mocked_smtp(self):
        tool = EmailTool(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="pass",
        )
        # Patch the module-level aiosmtplib reference and the availability flag
        with (
            patch("firefly_dworkers.tools.communication.email.AIOSMTPLIB_AVAILABLE", True),
            patch("firefly_dworkers.tools.communication.email.aiosmtplib") as mock_smtp,
        ):
            mock_smtp.send = AsyncMock()
            result = await tool.execute(action="send", channel="to@example.com", content="Hello!")
        assert result["channel"] == "to@example.com"
        assert result["content"] == "Hello!"
        assert result["sender"] == "user@example.com"
        assert result["id"].startswith("email-")

    async def test_read_requires_imap_host(self):
        tool = EmailTool(username="u", password="p")
        with pytest.raises(ToolError, match="imap_host"):
            await tool.execute(action="read", channel="INBOX")

    async def test_read_requires_credentials(self):
        tool = EmailTool(imap_host="imap.example.com")
        with pytest.raises(ToolError, match="username"):
            await tool.execute(action="read", channel="INBOX")

    async def test_list_channels_requires_imap_host(self):
        tool = EmailTool(username="u", password="p")
        with pytest.raises(ToolError, match="imap_host"):
            await tool.execute(action="list_channels")

    async def test_list_channels_requires_credentials(self):
        tool = EmailTool(imap_host="imap.example.com")
        with pytest.raises(ToolError, match="username"):
            await tool.execute(action="list_channels")


# ---------------------------------------------------------------------------
# SlackTool
# ---------------------------------------------------------------------------


class TestSlackTool:
    def test_instantiation(self):
        tool = SlackTool()
        assert tool is not None

    def test_name(self):
        assert SlackTool().name == "slack"

    def test_tags(self):
        tags = SlackTool().tags
        assert "communication" in tags
        assert "slack" in tags

    def test_is_base_tool(self):
        assert isinstance(SlackTool(), BaseTool)

    def test_config_params(self):
        tool = SlackTool(
            bot_token="xoxb-token",
            app_token="xapp-token",
            default_channel="general",
            timeout=45.0,
        )
        assert tool._bot_token == "xoxb-token"
        assert tool._app_token == "xapp-token"
        assert tool._default_channel == "general"
        assert tool._timeout == 45.0

    async def test_send_requires_bot_token(self):
        tool = SlackTool()
        tool._ensure_deps = MagicMock()  # bypass dep check
        with pytest.raises(ToolError, match="bot_token"):
            await tool.execute(action="send", channel="general", content="Hi")

    async def test_send_requires_channel(self):
        tool = SlackTool(bot_token="xoxb-test")
        mock_client = MagicMock()
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        with pytest.raises(ToolError, match="channel"):
            await tool.execute(action="send", channel="", content="Hi")

    async def test_send_with_mocked_client(self):
        tool = SlackTool(bot_token="xoxb-test")
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="send", channel="#general", content="Hi team")
        assert result["id"] == "1234567890.123456"
        assert result["channel"] == "#general"
        assert result["content"] == "Hi team"

    async def test_read_with_mocked_client(self):
        tool = SlackTool(bot_token="xoxb-test")
        mock_client = MagicMock()
        mock_client.conversations_history.return_value = {
            "messages": [
                {"ts": "1234567890.1", "user": "U123", "text": "Hello!"},
                {"ts": "1234567890.2", "user": "U456", "text": "Hi there"},
            ]
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="read", channel="general")
        assert len(result) == 2
        assert result[0]["content"] == "Hello!"
        assert result[1]["sender"] == "U456"

    async def test_list_channels_with_mocked_client(self):
        tool = SlackTool(bot_token="xoxb-test")
        mock_client = MagicMock()
        mock_client.conversations_list.return_value = {
            "channels": [
                {"name": "general"},
                {"name": "random"},
                {"name": "engineering"},
            ]
        }
        tool._client = mock_client
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="list_channels")
        assert "general" in result
        assert "random" in result
        assert "engineering" in result


# ---------------------------------------------------------------------------
# TeamsTool
# ---------------------------------------------------------------------------


class TestTeamsTool:
    def test_instantiation(self):
        tool = TeamsTool()
        assert tool is not None

    def test_name(self):
        assert TeamsTool().name == "teams"

    def test_tags(self):
        tags = TeamsTool().tags
        assert "communication" in tags
        assert "teams" in tags

    def test_is_base_tool(self):
        assert isinstance(TeamsTool(), BaseTool)

    def test_config_params(self):
        tool = TeamsTool(
            tenant_id="t1",
            client_id="c1",
            client_secret="s1",
            team_id="team-123",
            timeout=60.0,
        )
        assert tool._tenant_id == "t1"
        assert tool._client_id == "c1"
        assert tool._client_secret == "s1"
        assert tool._team_id == "team-123"
        assert tool._timeout == 60.0

    async def test_send_requires_team_id(self):
        tool = TeamsTool(tenant_id="t", client_id="c", client_secret="s")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="team_id"):
            await tool.execute(action="send", channel="ch-1", content="Update")

    async def test_send_requires_channel(self):
        tool = TeamsTool(tenant_id="t", client_id="c", client_secret="s", team_id="team-1")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]
        with pytest.raises(ToolError, match="channel"):
            await tool.execute(action="send", channel="", content="Update")

    async def test_send_with_mocked_graph(self):
        tool = TeamsTool(tenant_id="t", client_id="c", client_secret="s", team_id="team-1")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._graph_post = AsyncMock(
            return_value={  # type: ignore[method-assign]
                "id": "msg-001",
                "from": {"user": {"displayName": "Bot"}},
                "createdDateTime": "2025-01-01T00:00:00Z",
            }
        )
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="send", channel="ch-1", content="Update")
        assert result["id"] == "msg-001"
        assert result["channel"] == "ch-1"
        assert result["content"] == "Update"

    async def test_read_with_mocked_graph(self):
        tool = TeamsTool(tenant_id="t", client_id="c", client_secret="s", team_id="team-1")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._graph_get = AsyncMock(
            return_value={  # type: ignore[method-assign]
                "value": [
                    {
                        "id": "msg-001",
                        "from": {"user": {"displayName": "Alice"}},
                        "body": {"content": "Hello team"},
                        "createdDateTime": "2025-01-01T00:00:00Z",
                    },
                ]
            }
        )
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="read", channel="ch-1")
        assert len(result) == 1
        assert result[0]["content"] == "Hello team"
        assert result[0]["sender"] == "Alice"

    async def test_list_channels_with_mocked_graph(self):
        tool = TeamsTool(tenant_id="t", client_id="c", client_secret="s", team_id="team-1")
        tool._get_token = AsyncMock(return_value="fake-token")  # type: ignore[method-assign]
        tool._graph_get = AsyncMock(
            return_value={  # type: ignore[method-assign]
                "value": [
                    {"displayName": "General"},
                    {"displayName": "Engineering"},
                ]
            }
        )
        tool._ensure_deps = MagicMock()  # type: ignore[method-assign]

        result = await tool.execute(action="list_channels")
        assert "General" in result
        assert "Engineering" in result

    async def test_auth_requires_credentials(self):
        """Without credentials, teams operations fail (may hit team_id check first)."""
        tool = TeamsTool()
        tool._ensure_deps = MagicMock()  # bypass dep check
        with pytest.raises(ToolError, match="team_id|tenant_id|client_id|client_secret"):
            await tool.execute(action="list_channels")
