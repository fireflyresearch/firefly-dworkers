"""Tests for CommandRouter — slash command text generation without Textual."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from firefly_dworkers_cli.tui.commands import WELCOME_TEXT, CommandRouter


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
        assert "**Commands**" in text
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

    def test_checkpoints_text_no_pending(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.checkpoints_text()
        assert "No pending checkpoints" in text

    def test_checkpoints_text_with_pending(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        # Manually submit a checkpoint to the internal store
        handler._store.submit("cp_001", {"draft": "hello"}, worker_name="Analyst", phase="review")
        handler._store.submit("cp_002", {"data": [1, 2]}, worker_name="Researcher", phase="analysis")

        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.checkpoints_text()
        assert "Pending Checkpoints" in text
        assert "cp_001" in text
        assert "Analyst" in text
        assert "review" in text
        assert "cp_002" in text
        assert "Researcher" in text
        assert "analysis" in text
        assert "/approve" in text
        assert "/reject" in text


class TestApproveText:
    def test_approve_no_handler(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.approve_text("cp_001")
        assert "No checkpoint handler" in text

    def test_approve_no_id(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.approve_text("")
        assert "Usage" in text

    def test_approve_not_found(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.approve_text("nonexistent")
        assert "not found" in text.lower()

    def test_approve_success(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        handler._store.submit("cp_abc", {"draft": "hi"}, worker_name="Analyst", phase="review")
        # Also register the asyncio event so approve() can call .set()
        import asyncio
        handler._events["cp_abc"] = asyncio.Event()
        handler._results["cp_abc"] = False

        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.approve_text("cp_abc")
        assert "Approved" in text or "approved" in text
        assert "cp_abc" in text


class TestRejectText:
    def test_reject_no_handler(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.reject_text("cp_001")
        assert "No checkpoint handler" in text

    def test_reject_no_id(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.reject_text("")
        assert "Usage" in text

    def test_reject_not_found(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.reject_text("nonexistent")
        assert "not found" in text.lower()

    def test_reject_success(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        handler._store.submit("cp_xyz", {"data": [1]}, worker_name="Researcher", phase="analysis")
        import asyncio
        handler._events["cp_xyz"] = asyncio.Event()
        handler._results["cp_xyz"] = False

        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.reject_text("cp_xyz", reason="needs revision")
        assert "Rejected" in text or "rejected" in text
        assert "cp_xyz" in text

    def test_reject_success_no_reason(self):
        from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler

        handler = TUICheckpointHandler()
        handler._store.submit("cp_nnn", {"data": []}, worker_name="Designer", phase="draft")
        import asyncio
        handler._events["cp_nnn"] = asyncio.Event()
        handler._results["cp_nnn"] = False

        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        router.checkpoint_handler = handler
        text = router.reject_text("cp_nnn")
        assert "Rejected" in text or "rejected" in text
        assert "cp_nnn" in text


class TestNewCommands:
    def test_usage_in_commands(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert "/usage" in router.commands

    def test_delete_in_commands(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert "/delete" in router.commands

    def test_clear_in_commands(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert "/clear" in router.commands

    def test_retry_in_commands(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert "/retry" in router.commands

    def test_models_in_commands(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert "/models" in router.commands

    def test_model_in_commands(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert "/model" in router.commands


class TestUsageText:
    def test_usage_text_no_client(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.usage_text()
        assert "Not connected" in text


class TestDeleteText:
    def test_delete_no_id(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.delete_text("")
        assert "Usage" in text

    def test_delete_not_found(self):
        store = _make_store()
        store.delete_conversation.return_value = False
        router = CommandRouter(client=None, store=store, config_mgr=_make_config_mgr())
        text = router.delete_text("nonexistent")
        assert "not found" in text.lower()

    def test_delete_success(self):
        store = _make_store()
        store.delete_conversation.return_value = True
        router = CommandRouter(client=None, store=store, config_mgr=_make_config_mgr())
        text = router.delete_text("conv_123")
        assert "Deleted" in text


class TestModelsText:
    def test_models_text_no_config(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr(config=None))
        text = router.models_text()
        assert "No configuration" in text

    def test_models_text_with_config(self):
        config = MagicMock()
        config.models.default = "openai:gpt-5.2"
        mgr = _make_config_mgr(config=config)
        mgr.model_provider.return_value = "openai"
        mgr.detect_api_keys.return_value = {"openai": "sk-xxx"}
        router = CommandRouter(client=None, store=_make_store(), config_mgr=mgr)
        text = router.models_text()
        assert "gpt-5.2" in text
        assert "openai" in text


class TestModelText:
    def test_model_text_no_arg(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.model_text("")
        assert "Usage" in text

    def test_model_text_switch(self):
        config = MagicMock()
        config.models.default = "openai:gpt-5.2"
        mgr = _make_config_mgr(config=config)
        router = CommandRouter(client=None, store=_make_store(), config_mgr=mgr)
        text = router.model_text("anthropic:claude-sonnet-4-5-20250929")
        assert "Switched" in text


class TestWelcomeTextMinimal:
    def test_welcome_text_is_short(self):
        """Welcome text should be concise — 20 lines or fewer (including mascot)."""
        lines = [l for l in WELCOME_TEXT.strip().split("\n") if l.strip()]
        assert len(lines) <= 20

    def test_welcome_text_mentions_help(self):
        assert "/help" in WELCOME_TEXT

    def test_welcome_text_mentions_manager(self):
        assert "@manager" in WELCOME_TEXT


class TestDefaultRoleIsManager:
    def test_welcome_text_mentions_manager_default(self):
        assert "manager" in WELCOME_TEXT.lower()

    def test_help_text_mentions_manager_default(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert "`@manager`" in router.help_text


class TestNewCommandsRegistered:
    @pytest.mark.parametrize("cmd", ["/invite", "/private", "/attach", "/detach"])
    def test_new_command_registered(self, cmd):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        assert cmd in router.commands


class TestInviteText:
    def test_invite_no_arg(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.invite_text("")
        assert "Usage" in text

    def test_invite_valid_role(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.invite_text("researcher", known_roles={"researcher", "analyst"})
        assert "Invited" in text
        assert "@researcher" in text

    def test_invite_unknown_role(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.invite_text("wizard", known_roles={"researcher", "analyst"})
        assert "Unknown role" in text

    def test_invite_strips_at_sign(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.invite_text("@researcher", known_roles={"researcher"})
        assert "Invited" in text
        assert "@researcher" in text


class TestPrivateText:
    def test_private_enter(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.private_text("researcher")
        assert "private" in text.lower()
        assert "@researcher" in text

    def test_private_exit(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.private_text(None)
        assert "Exited" in text or "exit" in text.lower()


class TestAttachText:
    def test_attach_no_arg(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.attach_text("")
        assert "Usage" in text

    def test_attach_with_path(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.attach_text("report.pdf")
        assert "Attached" in text
        assert "report.pdf" in text


class TestDetachText:
    def test_detach(self):
        router = CommandRouter(client=None, store=_make_store(), config_mgr=_make_config_mgr())
        text = router.detach_text()
        assert "cleared" in text.lower() or "Cleared" in text


class TestTeamDisplayWithIdentities:
    def test_welcome_text_mentions_amara(self):
        from firefly_dworkers_cli.tui.commands import WELCOME_TEXT
        assert "Amara" in WELCOME_TEXT

    def test_welcome_text_has_mascot(self):
        from firefly_dworkers_cli.tui.commands import WELCOME_TEXT
        assert "dworkers" in WELCOME_TEXT


class TestContextCommands:
    def test_context_command_registered(self):
        from firefly_dworkers_cli.tui.commands import _COMMANDS
        assert "/context" in _COMMANDS

    def test_compact_command_registered(self):
        from firefly_dworkers_cli.tui.commands import _COMMANDS
        assert "/compact" in _COMMANDS


class TestConversationManagementCommands:
    def test_list_command_registered(self):
        from firefly_dworkers_cli.tui.commands import _COMMANDS
        assert "/list" in _COMMANDS

    def test_search_command_registered(self):
        from firefly_dworkers_cli.tui.commands import _COMMANDS
        assert "/search" in _COMMANDS

    def test_rename_command_registered(self):
        from firefly_dworkers_cli.tui.commands import _COMMANDS
        assert "/rename" in _COMMANDS

    def test_archive_command_registered(self):
        from firefly_dworkers_cli.tui.commands import _COMMANDS
        assert "/archive" in _COMMANDS
