"""CommandRouter — slash command text generation without Textual dependencies.

Every method returns a plain string (typically markdown). The TUI app mounts
the returned text into the UI. This separation makes commands testable without
any Textual widget tree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from firefly_dworkers_cli.config import ConfigManager
    from firefly_dworkers_cli.tui.backend.client import DworkersClient
    from firefly_dworkers_cli.tui.backend.models import Conversation
    from firefly_dworkers_cli.tui.backend.store import ConversationStore

WELCOME_TEXT = """\
  dworkers — Digital Workers as a Service

  Type a message to start chatting with your AI workers.
  Use @analyst, @researcher, @designer to target a specific worker.

  Commands:
    /help          Show all commands
    /team          List available workers
    /plan          List workflow plans
    /conversations List saved conversations
    /load <id>     Load a saved conversation
    /config        Current configuration
    /connectors    Connector statuses
    /status        Current session info
    /export        Export conversation
    /new           Start a new conversation
    /autonomy      Show or set autonomy level
    /quit          Exit
"""

_HELP_TEXT = """\
Available commands:
  /help              Show this help message
  /team              List available AI workers and their status
  /plan              List available workflow plans
  /plan <name>       Execute a named plan
  /project <brief>   Run a multi-worker project
  /conversations     List all saved conversations
  /load <id>         Load a saved conversation
  /new               Start a fresh conversation
  /status            Show current session status
  /config            Show current configuration
  /connectors        List all connector statuses
  /send <tool> <ch>  Send a message via Slack/Teams/email
  /channels <tool>   List channels for a messaging tool
  /export            Export current conversation as markdown
  /autonomy [level]  Show or change autonomy level
  /checkpoints       List pending checkpoints
  /setup             Re-run the setup wizard
  /quit              Exit dworkers

Tips:
  - Use @analyst, @researcher, @data_analyst, @manager, @designer
    to route your message to a specific worker role
  - Default worker is @analyst if no role is specified
  - Messages support markdown formatting
  - Use /send slack #general <message> to send via Slack
  - Use /channels slack to list Slack channels
"""

# All recognised command names (must include the leading slash).
_COMMANDS: set[str] = {
    "/help",
    "/team",
    "/plan",
    "/project",
    "/conversations",
    "/load",
    "/new",
    "/status",
    "/config",
    "/connectors",
    "/send",
    "/channels",
    "/export",
    "/autonomy",
    "/checkpoints",
    "/approve",
    "/reject",
    "/setup",
    "/quit",
}


class CommandRouter:
    """Pure-text command handler — no widget dependencies."""

    WELCOME_TEXT: str = WELCOME_TEXT

    def __init__(
        self,
        *,
        client: DworkersClient | None,
        store: ConversationStore,
        config_mgr: ConfigManager,
    ) -> None:
        self.client = client
        self._store = store
        self._config_mgr = config_mgr
        self.autonomy_level: str = "semi_supervised"
        self.checkpoint_handler = None  # Will be set later for Task 7

    # -- metadata -------------------------------------------------------------

    @property
    def commands(self) -> set[str]:
        """All recognised slash-command names."""
        return _COMMANDS

    @property
    def help_text(self) -> str:
        """The full help message."""
        return _HELP_TEXT

    @staticmethod
    def parse(text: str) -> tuple[str, str]:
        """Split raw input into ``(command, args)``."""
        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        return command, arg

    # -- text generators (sync, no widgets) -----------------------------------

    def conversations_text(self) -> str:
        """Markdown listing of saved conversations with IDs."""
        convos = self._store.list_conversations()
        if not convos:
            return "No saved conversations."
        lines = ["**Saved Conversations:**\n"]
        for c in convos:
            updated = c.updated_at.strftime("%b %d, %H:%M")
            lines.append(
                f"- `{c.id}` — **{c.title}** ({c.message_count} msgs, {updated})"
            )
        return "\n".join(lines)

    def status_text(
        self,
        conversation: Conversation | None,
        total_tokens: int,
    ) -> str:
        """Session status string."""
        if conversation:
            lines = [
                "**Session Status:**\n",
                f"- **Conversation:** {conversation.title}",
                f"- **Status:** {conversation.status}",
                f"- **Messages:** {len(conversation.messages)}",
                f"- **Tokens:** {total_tokens:,}",
            ]
            if conversation.participants:
                lines.append(
                    f"- **Participants:** {', '.join(conversation.participants)}"
                )
        else:
            lines = [
                "**Session Status:**\n",
                "- No active conversation",
                f"- **Tokens:** {total_tokens:,}",
                "- Type a message to start",
            ]
        return "\n".join(lines)

    def export_text(self, conversation: Conversation | None) -> str:
        """Export the current conversation as markdown."""
        if not conversation or not conversation.messages:
            return "Nothing to export."
        lines = [f"# {conversation.title}\n"]
        for msg in conversation.messages:
            ts = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            lines.append(f"**{msg.sender}** ({ts}):\n\n{msg.content}\n\n---\n")
        return "\n".join(lines)

    def config_text(self) -> str:
        """Current configuration as a markdown string."""
        config = self._config_mgr.config
        if config is None:
            return "No configuration loaded."
        enabled_connectors = config.connectors.enabled_connectors()
        connector_names = ", ".join(sorted(enabled_connectors.keys())) or "none"
        api_keys = self._config_mgr.detect_api_keys()
        providers = ", ".join(p.title() for p in sorted(api_keys)) or "none"
        lines = [
            "**Current Configuration:**\n",
            f"- **Tenant:** {config.name} (`{config.id}`)",
            f"- **Default Model:** `{config.models.default}`",
            f"- **Research Model:** `{config.models.research or 'same as default'}`",
            f"- **Analysis Model:** `{config.models.analysis or 'same as default'}`",
            f"- **Available Providers:** {providers}",
            f"- **Enabled Connectors:** {connector_names}",
            f"- **Global Config:** `{self._config_mgr.global_config_path}`",
            f"- **Project Config:** `{self._config_mgr.project_config_path}`",
        ]
        return "\n".join(lines)

    # -- autonomy / checkpoints (placeholders for Task 7) ---------------------

    _VALID_AUTONOMY_LEVELS = {"manual", "semi_supervised", "autonomous"}

    def autonomy_text(self, new_level: str | None = None) -> str:
        """Show or change the autonomy level.

        If *new_level* is provided and valid, the level is updated.
        """
        if new_level is not None:
            if new_level not in self._VALID_AUTONOMY_LEVELS:
                return (
                    f"Invalid autonomy level: `{new_level}`\n\n"
                    f"Valid levels: {', '.join(sorted(self._VALID_AUTONOMY_LEVELS))}"
                )
            self.autonomy_level = new_level
        return (
            f"**Autonomy Level:** `{self.autonomy_level}`\n\n"
            "Levels: `manual`, `semi_supervised`, `autonomous`\n"
            "Usage: `/autonomy <level>` to change."
        )

    def checkpoints_text(self) -> str:
        """List pending checkpoints (placeholder for Task 7)."""
        if self.checkpoint_handler is None:
            return "No checkpoint handler configured."
        # Will be implemented in Task 7
        return "No pending checkpoints."
