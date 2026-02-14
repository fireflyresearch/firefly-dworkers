"""Tests for CommandRouter — slash command text generation without Textual."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from firefly_dworkers_cli.tui.commands import CommandRouter


def _make_store(conversations=None):
    """Return a mock ConversationStore."""
    store = MagicMock()
    store.list_conversations.return_value = conversations or []
    return store


def _make_config_mgr(*, config=None):
    """Return a mock ConfigManager."""
    mgr = MagicMock()
    mgr.config = config
    mgr.global_config_path = "/home/user/.dworkers/config.yaml"
    mgr.project_config_path = "/project/.dworkers/config.yaml"
    mgr.detect_api_keys.return_value = {}
    return mgr


class TestCommandRouterInstantiation:
    def test_instantiates(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert router.client is None
        assert router.autonomy_level == "semi_supervised"
        assert router.checkpoint_handler is None


class TestCommandRouterCommands:
    def test_known_commands(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        cmds = router.commands
        # All commands mentioned in help text must be registered
        for cmd in [
            "/help", "/team", "/plan", "/project", "/conversations",
            "/load", "/new", "/status", "/config", "/connectors",
            "/send", "/channels", "/export", "/setup", "/quit", "/autonomy",
        ]:
            assert cmd in cmds, f"{cmd} not in commands"


class TestCommandRouterParse:
    def test_parse_command(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        cmd, arg = router.parse("/team some args")
        assert cmd == "/team"
        assert arg == "some args"

    def test_parse_command_no_arg(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        cmd, arg = router.parse("/help")
        assert cmd == "/help"
        assert arg == ""

    def test_parse_command_lowercases(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        cmd, arg = router.parse("/HELP")
        assert cmd == "/help"


class TestHelpText:
    def test_help_text(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.help_text
        assert "Available commands:" in text
        assert "/autonomy" in text
        assert "/help" in text
        assert "/export" in text


class TestConfigText:
    def test_config_text_no_config(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr(config=None))
        text = router.config_text()
        assert "No configuration loaded" in text

    def test_config_text_with_config(self):
        config = MagicMock()
        config.name = "TestTenant"
        config.id = "test-id"
        config.models.default = "openai:gpt-4o"
        config.models.research = ""
        config.models.analysis = ""
        config.connectors.enabled_connectors.return_value = {"slack": True}
        mgr = _make_config_mgr(config=config)
        mgr.detect_api_keys.return_value = {"openai": "sk-xxx"}
        router = CommandRouter(client=None, store=_make_store(), config_mgr=mgr)
        text = router.config_text()
        assert "TestTenant" in text
        assert "test-id" in text
        assert "gpt-4o" in text


class TestConversationsText:
    def test_conversations_text_empty(self):
        router = CommandRouter(client=None, store=_make_store(conversations=[]), config_mgr=_make_config_mgr())
        text = router.conversations_text()
        assert "No saved conversations" in text

    def test_conversations_text_shows_ids(self):
        conv = MagicMock()
        conv.id = "conv_abc123"
        conv.title = "Test Chat"
        conv.updated_at = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        conv.message_count = 5
        store = _make_store(conversations=[conv])
        router = CommandRouter(client=None, store=store, config_mgr=_make_config_mgr())
        text = router.conversations_text()
        assert "conv_abc123" in text
        assert "Test Chat" in text
        assert "5" in text


class TestStatusText:
    def test_status_text_no_conversation(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.status_text(conversation=None, total_tokens=0)
        assert "No active conversation" in text

    def test_status_text_with_conversation(self):
        conv = MagicMock()
        conv.title = "My Chat"
        conv.status = "active"
        conv.messages = [MagicMock(), MagicMock()]
        conv.participants = ["analyst", "researcher"]
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.status_text(conversation=conv, total_tokens=1500)
        assert "My Chat" in text
        assert "active" in text
        assert "2" in text
        assert "1,500" in text
        assert "analyst" in text


class TestExportText:
    def test_export_text_no_conversation(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.export_text(conversation=None)
        assert "Nothing to export" in text

    def test_export_text_empty_messages(self):
        conv = MagicMock()
        conv.messages = []
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.export_text(conversation=conv)
        assert "Nothing to export" in text

    def test_export_text_with_messages(self):
        conv = MagicMock()
        conv.title = "Export Chat"
        msg = MagicMock()
        msg.sender = "You"
        msg.timestamp = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        msg.content = "Hello world"
        conv.messages = [msg]
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.export_text(conversation=conv)
        assert "Export Chat" in text
        assert "Hello world" in text
        assert "You" in text


class TestAutonomyText:
    def test_autonomy_text_shows_level(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.autonomy_text()
        assert "semi_supervised" in text

    def test_autonomy_text_changes_level(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.autonomy_text(new_level="autonomous")
        assert router.autonomy_level == "autonomous"
        assert "autonomous" in text

    def test_autonomy_text_rejects_invalid_level(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.autonomy_text(new_level="full")
        assert router.autonomy_level == "semi_supervised"  # unchanged
        assert "Invalid" in text


class TestCheckpointsText:
    def test_checkpoints_text_no_handler(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.checkpoints_text()
        assert "No checkpoint handler" in text or "no pending" in text.lower()
