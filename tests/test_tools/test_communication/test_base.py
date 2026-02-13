"""Tests for MessageTool abstract base."""

from __future__ import annotations

import pytest

from firefly_dworkers.tools.communication.base import Message, MessageTool


class FakeMessageTool(MessageTool):
    """Concrete implementation for testing."""

    async def _send(self, channel: str, content: str) -> Message:
        return Message(
            id="msg-1",
            channel=channel,
            sender="bot",
            content=content,
            timestamp="2026-01-01T00:00:00Z",
        )

    async def _read(self, channel: str, message_id: str) -> list[Message]:
        return [
            Message(
                id=message_id or "msg-1",
                channel=channel,
                sender="user",
                content="Hello there",
                timestamp="2026-01-01T00:00:00Z",
            )
        ]

    async def _list_channels(self) -> list[str]:
        return ["general", "random", "project-alpha"]


class TestMessageTool:
    async def test_send_action(self):
        tool = FakeMessageTool("test_chat")
        result = await tool.execute(action="send", channel="general", content="Hello!")
        assert result["id"] == "msg-1"
        assert result["channel"] == "general"
        assert result["content"] == "Hello!"
        assert result["sender"] == "bot"

    async def test_read_action(self):
        tool = FakeMessageTool("test_chat")
        result = await tool.execute(action="read", channel="general", message_id="msg-5")
        assert len(result) == 1
        assert result[0]["id"] == "msg-5"
        assert result[0]["channel"] == "general"
        assert result[0]["content"] == "Hello there"

    async def test_list_channels_action(self):
        tool = FakeMessageTool("test_chat")
        result = await tool.execute(action="list_channels")
        assert result == ["general", "random", "project-alpha"]

    async def test_unknown_action_raises(self):
        tool = FakeMessageTool("test_chat")
        with pytest.raises(Exception, match="Unknown action"):
            await tool.execute(action="delete")

    def test_name(self):
        tool = FakeMessageTool("slack")
        assert tool.name == "slack"

    def test_tags(self):
        tool = FakeMessageTool("slack")
        assert "communication" in tool.tags
        assert "messaging" in tool.tags
        assert "slack" in tool.tags

    def test_description_default(self):
        tool = FakeMessageTool("slack")
        assert "slack" in tool.description

    def test_description_custom(self):
        tool = FakeMessageTool("slack", description="Slack messaging integration")
        assert tool.description == "Slack messaging integration"

    def test_parameters(self):
        tool = FakeMessageTool("test_chat")
        param_names = [p.name for p in tool.parameters]
        assert "action" in param_names
        assert "channel" in param_names
        assert "content" in param_names
        assert "message_id" in param_names

    def test_is_base_tool(self):
        from fireflyframework_genai.tools.base import BaseTool

        assert isinstance(FakeMessageTool("test"), BaseTool)
