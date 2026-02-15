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
  dworkers v0.1.0

  Your AI team of specialized workers — manager, analyst, researcher, designer, and more.

  Getting started:
    Messages go to @manager by default — your AI team lead who routes tasks and launches plans.
    Use @role to target a specific worker (e.g., @researcher summarize...).
    Use /plan <name> to run multi-step workflows across workers.
    Use /project <brief> to orchestrate a full project with all workers.

  /help for all commands · /team to see your workers\
"""

_HELP_TEXT = """\
Available commands:
  /help              Show this help message
  /team              List available AI workers and their status
  /invite <role>     Invite a worker to the conversation
  /private [role]    Start/end a private conversation with a worker
  /plan              List available workflow plans
  /plan <name>       Execute a named plan
  /project <brief>   Run a multi-worker project
  /attach <path>     Attach a file to the next message
  /detach            Clear all file attachments
  /conversations     List all saved conversations
  /load <id>         Load a saved conversation
  /new               Start a fresh conversation
  /delete <id>       Delete a saved conversation
  /clear             Clear the chat display
  /retry             Retry the last user message
  /status            Show current session status
  /config            Show current configuration
  /connectors        List all connector statuses
  /models            Show available models and providers
  /model <name>      Switch the default model
  /usage             Show usage statistics
  /send <tool> <ch>  Send a message via Slack/Teams/email
  /channels <tool>   List channels for a messaging tool
  /export            Export current conversation as markdown
  /autonomy [level]  Show or change autonomy level
  /checkpoints       List pending checkpoints
  /approve <id>      Approve a pending checkpoint
  /reject <id>       Reject a pending checkpoint (with optional reason)
  /setup             Re-run the setup wizard
  /quit              Exit dworkers

Tips:
  - Type @role to route messages to a specific worker (autocomplete with Tab)
  - Default worker is @manager — your team lead who routes tasks and launches plans
  - Use /invite to bring workers into the conversation
  - Use /private @role for focused 1-on-1 sessions
  - Attach files with /attach <path> (images, PDFs, code, text)
  - Messages support markdown formatting
  - Press Escape during streaming to cancel
  - Use /autonomy to view or change the autonomy level
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
    "/usage",
    "/delete",
    "/clear",
    "/retry",
    "/models",
    "/model",
    "/invite",
    "/private",
    "/attach",
    "/detach",
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
        self.checkpoint_handler = None  # Set by app after TUICheckpointHandler is created

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

    # -- new commands ----------------------------------------------------------

    def usage_text(self) -> str:
        """Return usage statistics text."""
        if self.client is None:
            return "**Error:** Not connected to a backend."
        return (
            "Usage statistics are available after running workers.\n\n"
            "Use `/status` to see current session stats."
        )

    def delete_text(self, conv_id: str) -> str:
        """Delete a conversation by ID."""
        conv_id = conv_id.strip()
        if not conv_id:
            return "Usage: `/delete <conversation-id>`\n\nUse `/conversations` to see IDs."
        deleted = self._store.delete_conversation(conv_id)
        if deleted:
            return f"Deleted conversation `{conv_id}`."
        return f"**Error:** Conversation `{conv_id}` not found."

    def models_text(self) -> str:
        """Return available models for the current provider."""
        config = self._config_mgr.config
        if config is None:
            return "**Error:** No configuration loaded. Run `/setup`."
        current = config.models.default
        provider = self._config_mgr.model_provider(current)
        lines = [f"**Current model:** `{current}`\n", f"**Provider:** {provider}\n"]
        detected_keys = self._config_mgr.detect_api_keys()
        if detected_keys:
            lines.append("**Available providers:** " + ", ".join(sorted(detected_keys.keys())))
        return "\n".join(lines)

    def model_text(self, model_name: str) -> str:
        """Switch the default model."""
        model_name = model_name.strip()
        if not model_name:
            return "Usage: `/model <provider:model-name>`\n\nExample: `/model openai:gpt-5.2`"
        config = self._config_mgr.config
        if config is None:
            return "**Error:** No configuration loaded. Run `/setup`."
        old_model = config.models.default
        config.models.default = model_name
        return f"Switched model: `{old_model}` \u2192 `{model_name}`"

    # -- autonomy / checkpoints ------------------------------------------------

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
        """List pending checkpoints."""
        if self.checkpoint_handler is None:
            return "No checkpoint handler configured."
        pending = self.checkpoint_handler.list_pending()
        if not pending:
            return "No pending checkpoints."
        lines = ["**Pending Checkpoints:**\n"]
        for cp in pending:
            lines.append(f"- `{cp.id}` -- **{cp.worker_name}** at _{cp.phase}_")
        lines.append("\nUse `/approve <id>` or `/reject <id> [reason]` to resolve.")
        return "\n".join(lines)

    def approve_text(self, checkpoint_id: str) -> str:
        """Approve a pending checkpoint and return status text."""
        if self.checkpoint_handler is None:
            return "No checkpoint handler configured."
        checkpoint_id = checkpoint_id.strip()
        if not checkpoint_id:
            return "Usage: `/approve <checkpoint-id>`"
        cp = self.checkpoint_handler.get(checkpoint_id)
        if cp is None:
            return f"Checkpoint `{checkpoint_id}` not found."
        self.checkpoint_handler.approve(checkpoint_id)
        return f"Approved checkpoint `{checkpoint_id}` (**{cp.worker_name}** at _{cp.phase}_)."

    def reject_text(self, checkpoint_id: str, *, reason: str = "") -> str:
        """Reject a pending checkpoint and return status text."""
        if self.checkpoint_handler is None:
            return "No checkpoint handler configured."
        checkpoint_id = checkpoint_id.strip()
        if not checkpoint_id:
            return "Usage: `/reject <checkpoint-id> [reason]`"
        cp = self.checkpoint_handler.get(checkpoint_id)
        if cp is None:
            return f"Checkpoint `{checkpoint_id}` not found."
        self.checkpoint_handler.reject(checkpoint_id, reason=reason)
        reason_suffix = f" Reason: {reason}" if reason else ""
        return f"Rejected checkpoint `{checkpoint_id}` (**{cp.worker_name}** at _{cp.phase}_).{reason_suffix}"

    # -- invite / private / attach / detach ------------------------------------

    def invite_text(self, role: str, *, known_roles: set[str] | None = None) -> str:
        """Validate and confirm inviting a worker to the conversation."""
        role = role.strip().lstrip("@").lower()
        if not role:
            return "Usage: `/invite <role>`\n\nExample: `/invite researcher`"
        if known_roles and role not in known_roles:
            available = ", ".join(sorted(known_roles))
            return f"Unknown role: `{role}`\n\nAvailable: {available}"
        return f"Invited **@{role}** to the conversation."

    def private_text(self, role: str | None) -> str:
        """Return text for entering or exiting private conversation mode."""
        if role:
            role = role.strip().lstrip("@").lower()
            return f"Entering private conversation with **@{role}**. All messages will go to @{role}.\n\nUse `/private` to exit."
        return "Exited private mode. Messages route normally."

    def attach_text(self, path: str) -> str:
        """Return confirmation text for attaching a file."""
        path = path.strip()
        if not path:
            return "Usage: `/attach <file-path>`\n\nExample: `/attach ~/report.pdf`"
        return f"Attached **{path}**."

    def detach_text(self) -> str:
        """Return confirmation text for clearing all attachments."""
        return "All attachments cleared."
