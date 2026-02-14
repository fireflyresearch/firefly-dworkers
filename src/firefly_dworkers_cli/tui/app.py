"""DworkersApp — chat-first TUI matching Claude Code's terminal experience.

The entire app is a single chat view: messages scroll upward, input is
docked at the bottom, and a status bar shows model/connection info.
All features (settings, team, plans, etc.) are accessible via slash commands.

On first run (or when no usable config exists), the app launches a setup
wizard to configure the LLM provider and API keys.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Markdown, Static, TextArea

from firefly_dworkers_cli.config import ConfigManager
from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.backend.models import ChatMessage, Conversation
from firefly_dworkers_cli.tui.backend.store import ConversationStore
from firefly_dworkers_cli.tui.theme import APP_CSS

# Known worker roles for @mention detection.
_KNOWN_ROLES = {"analyst", "researcher", "data_analyst", "manager", "designer"}
_MENTION_RE = re.compile(r"@(\w+)")

_WELCOME_TEXT = """\
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


class DworkersApp(App):
    """Chat-first TUI for dworkers — inspired by Claude Code."""

    TITLE = "dworkers"
    CSS = APP_CSS

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+n", "new_conversation", "New Chat", show=False),
        Binding("escape", "focus_input", "Focus Input", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config_mgr = ConfigManager()
        self._store = ConversationStore()
        self._client: DworkersClient | None = None
        self._conversation: Conversation | None = None
        self._total_tokens = 0
        self._is_streaming = False

    def compose(self) -> ComposeResult:
        # Header bar
        with Horizontal(id="header-bar"):
            yield Static("dworkers", classes="header-title")
            yield Static("Ctrl+N new | Ctrl+Q quit", classes="header-hint")

        # Welcome banner (shown initially, hidden once chat starts)
        with Vertical(id="welcome"):
            yield Static(_WELCOME_TEXT, classes="welcome-hint")

        # Message list (hidden initially, shown once chat starts)
        yield VerticalScroll(id="message-list")

        # Input area
        with Vertical(id="input-area"):
            yield TextArea(id="prompt-input")
            yield Static("Enter to send | Shift+Enter for newline | /help for commands", classes="input-hint")

        # Status bar
        with Horizontal(id="status-bar"):
            yield Static("local", classes="status-item status-model")
            yield Static("\u2502", classes="status-item")
            yield Static("0 tokens", classes="status-item status-tokens", id="token-count")
            yield Static("\u25cf connected", classes="status-connection status-connected", id="conn-status")

    async def on_mount(self) -> None:
        """Load config, optionally run setup wizard, then connect to backend."""
        # Check if setup is needed
        if self._config_mgr.needs_setup():
            from firefly_dworkers_cli.tui.screens.setup import SetupScreen

            await self.push_screen(
                SetupScreen(self._config_mgr),
                callback=self._on_setup_complete,
            )
        else:
            # Load existing config and register in tenant_registry
            try:
                config = self._config_mgr.load()
                self._update_model_label(config.models.default)
            except Exception:
                pass
            await self._connect_and_focus()

    def _on_setup_complete(self, result: object) -> None:
        """Callback when setup wizard finishes."""
        if result is not None and hasattr(result, "models"):
            self._update_model_label(result.models.default)
        self.call_after_refresh(self._connect_and_focus)

    def _update_model_label(self, model_string: str) -> None:
        """Update the status bar model label."""
        try:
            # Show just the model name, not provider prefix
            if ":" in model_string:
                label = model_string.split(":", 1)[1]
            else:
                label = model_string
            self.query_one(".status-model", Static).update(label)
        except Exception:
            pass

    async def _connect_and_focus(self) -> None:
        """Connect to backend client and focus the input."""
        self._client = await create_client()

        # Update connection status
        conn = self.query_one("#conn-status", Static)
        client_type = type(self._client).__name__
        if client_type == "RemoteClient":
            conn.update("\u25cf remote")
            self._update_model_label("remote")
        else:
            conn.update("\u25cf local")

        # Focus the input
        self.query_one("#prompt-input", TextArea).focus()

    async def on_key(self, event) -> None:
        """Handle Enter to submit (without shift)."""
        input_widget = self.query_one("#prompt-input", TextArea)

        if event.key == "enter" and not event.shift:
            # Only handle if the input is focused
            if self.focused is input_widget:
                event.prevent_default()
                event.stop()
                text = input_widget.text.strip()
                if text and not self._is_streaming:
                    input_widget.clear()
                    await self._handle_input(text)

    async def _handle_input(self, text: str) -> None:
        """Route input to slash commands or message sending."""
        if text.startswith("/"):
            await self._handle_command(text)
        else:
            await self._send_message(text)

    # ── Message sending ──────────────────────────────────────

    async def _send_message(self, text: str) -> None:
        """Send a user message and stream the agent response."""
        self._hide_welcome()

        # Ensure we have a conversation
        if self._conversation is None:
            title = text[:50] + ("..." if len(text) > 50 else "")
            self._conversation = self._store.create_conversation(title)

        message_list = self.query_one("#message-list", VerticalScroll)

        # Add user message
        user_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            conversation_id=self._conversation.id,
            role="user",
            sender="You",
            content=text,
            timestamp=datetime.now(UTC),
            is_ai=False,
        )
        self._store.add_message(self._conversation.id, user_msg)
        self._add_user_message(message_list, text)

        # Determine target worker role
        role = self._extract_role(text) or "analyst"
        sender_name = role.replace("_", " ").title()

        # Add AI response header
        ai_header = Static(
            f"\u2726 {sender_name}",
            classes="msg-sender msg-sender-ai",
        )
        msg_box = Vertical(classes="msg-box")
        await message_list.mount(msg_box)
        await msg_box.mount(ai_header)

        # Create streaming content
        content_widget = Markdown("", classes="msg-content")
        await msg_box.mount(content_widget)

        indicator = Static("\u25cf\u25cf\u25cf working...", classes="streaming-indicator")
        await msg_box.mount(indicator)
        message_list.scroll_end(animate=False)

        # Stream from client
        self._is_streaming = True
        tokens: list[str] = []

        try:
            if self._client is not None:
                try:
                    async for event in self._client.run_worker(
                        role,
                        text,
                        conversation_id=self._conversation.id,
                    ):
                        if event.type in ("token", "complete"):
                            tokens.append(event.content)
                            await content_widget.update("".join(tokens))
                            message_list.scroll_end(animate=False)
                        elif event.type == "tool_call":
                            tool_box = Vertical(classes="tool-call")
                            await message_list.mount(tool_box)
                            await tool_box.mount(
                                Static(f"\u2699 {event.content}", classes="tool-call-header")
                            )
                            message_list.scroll_end(animate=False)
                        elif event.type == "error":
                            tokens.append(f"\n\n**Error:** {event.content}")
                            await content_widget.update("".join(tokens))
                except Exception as e:
                    tokens.append(f"\n\n**Connection error:** {e}")
                    await content_widget.update("".join(tokens))
        finally:
            self._is_streaming = False
            indicator.remove()

        # Save agent message
        final_content = "".join(tokens)
        agent_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            conversation_id=self._conversation.id,
            role=role,
            sender=sender_name,
            content=final_content,
            timestamp=datetime.now(UTC),
            is_ai=True,
        )
        self._store.add_message(self._conversation.id, agent_msg)

        # Update token count (rough estimate)
        self._total_tokens += len(final_content.split()) * 2
        self.query_one("#token-count", Static).update(
            f"{self._total_tokens:,} tokens"
        )

        message_list.scroll_end(animate=False)

    def _add_user_message(self, container: VerticalScroll, text: str) -> None:
        """Mount a user message into the message list."""
        msg_box = Vertical(classes="msg-box")
        header = Static("\u25cf You", classes="msg-sender msg-sender-human")
        content = Markdown(text, classes="msg-content")
        container.mount(msg_box)
        msg_box.mount(header)
        msg_box.mount(content)
        container.scroll_end(animate=False)

    def _add_system_message(self, container: VerticalScroll, text: str) -> None:
        """Mount a system message into the message list."""
        msg_box = Vertical(classes="cmd-output")
        content = Markdown(text, classes="cmd-output-content")
        container.mount(msg_box)
        msg_box.mount(content)
        container.scroll_end(animate=False)

    def _extract_role(self, text: str) -> str | None:
        """Return the first known @role mention in the message text."""
        for match in _MENTION_RE.finditer(text):
            mention = match.group(1).lower()
            if mention in _KNOWN_ROLES:
                return mention
        return None

    def _hide_welcome(self) -> None:
        """Hide the welcome banner and show the message list."""
        welcome = self.query_one("#welcome", Vertical)
        if welcome.display:
            welcome.display = False
            self.query_one("#message-list", VerticalScroll).display = True

    # ── Slash commands ───────────────────────────────────────

    async def _handle_command(self, text: str) -> None:
        """Handle slash commands."""
        self._hide_welcome()
        message_list = self.query_one("#message-list", VerticalScroll)
        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        match command:
            case "/help":
                self._add_system_message(message_list, _HELP_TEXT)

            case "/team":
                await self._cmd_team(message_list)

            case "/plan":
                if arg:
                    await self._cmd_execute_plan(message_list, arg)
                else:
                    await self._cmd_list_plans(message_list)

            case "/project":
                if arg:
                    await self._cmd_project(message_list, arg)
                else:
                    self._add_system_message(
                        message_list,
                        "Usage: `/project <brief>`\n\n"
                        "Example: `/project Analyze Q4 sales data and create a report`",
                    )

            case "/conversations":
                self._cmd_conversations(message_list)

            case "/load":
                self._cmd_load(message_list, arg)

            case "/new":
                self._conversation = None
                # Clear message list
                message_list.remove_children()
                self._add_system_message(
                    message_list,
                    "Started a new conversation. Type a message to begin.",
                )

            case "/status":
                self._cmd_status(message_list)

            case "/config":
                self._cmd_config(message_list)

            case "/connectors":
                await self._cmd_connectors(message_list)

            case "/send":
                await self._cmd_send(message_list, arg)

            case "/channels":
                await self._cmd_channels(message_list, arg)

            case "/export":
                self._cmd_export(message_list)

            case "/setup":
                await self._cmd_setup()

            case "/quit":
                self.exit()

            case _:
                self._add_system_message(
                    message_list,
                    f"Unknown command: `{command}`\n\nType `/help` for available commands.",
                )

    async def _cmd_team(self, container: VerticalScroll) -> None:
        """List available workers."""
        if self._client is None:
            self._add_system_message(container, "Client not connected.")
            return
        workers = await self._client.list_workers()
        lines = ["**Team Members:**\n"]
        for w in workers:
            status = "\u2713" if w.enabled else "\u2717"
            lines.append(f"- {status} **{w.name}** (`@{w.role}`) — {w.autonomy}")
        self._add_system_message(container, "\n".join(lines))

    async def _cmd_list_plans(self, container: VerticalScroll) -> None:
        """List available plans."""
        if self._client is None:
            self._add_system_message(container, "Client not connected.")
            return
        plans = await self._client.list_plans()
        if plans:
            lines = ["**Available Plans:**\n"]
            for p in plans:
                roles = ", ".join(p.worker_roles) if p.worker_roles else "none"
                lines.append(f"- **{p.name}** ({p.steps} steps) — workers: {roles}")
            self._add_system_message(container, "\n".join(lines))
        else:
            self._add_system_message(container, "No plans available.")

    async def _cmd_execute_plan(self, container: VerticalScroll, plan_name: str) -> None:
        """Execute a named plan with streaming output."""
        if self._client is None:
            self._add_system_message(container, "Client not connected.")
            return

        self._add_system_message(container, f"Executing plan: **{plan_name}**...")

        content = Markdown("", classes="msg-content")
        box = Vertical(classes="msg-box")
        header = Static(f"\u2726 Planner", classes="msg-sender msg-sender-ai")
        await container.mount(box)
        await box.mount(header)
        await box.mount(content)

        tokens: list[str] = []
        self._is_streaming = True
        try:
            async for event in self._client.execute_plan(plan_name):
                if event.type in ("token", "complete"):
                    tokens.append(event.content)
                    await content.update("".join(tokens))
                    container.scroll_end(animate=False)
                elif event.type == "error":
                    tokens.append(f"\n\n**Error:** {event.content}")
                    await content.update("".join(tokens))
        except Exception as e:
            tokens.append(f"\n\n**Error:** {e}")
            await content.update("".join(tokens))
        self._is_streaming = False

    def _cmd_conversations(self, container: VerticalScroll) -> None:
        """List saved conversations."""
        convos = self._store.list_conversations()
        if convos:
            lines = ["**Saved Conversations:**\n"]
            for c in convos:
                updated = c.updated_at.strftime("%b %d, %H:%M")
                lines.append(f"- **{c.title}** ({c.message_count} msgs, {updated})")
            self._add_system_message(container, "\n".join(lines))
        else:
            self._add_system_message(container, "No saved conversations.")

    def _cmd_load(self, container: VerticalScroll, conv_id: str) -> None:
        """Load a saved conversation by ID."""
        conv_id = conv_id.strip()
        if not conv_id:
            self._add_system_message(
                container,
                "Usage: `/load <conversation-id>`\n\n"
                "Use `/conversations` to see available IDs.",
            )
            return

        conv = self._store.get_conversation(conv_id)
        if conv is None:
            self._add_system_message(
                container, f"Conversation `{conv_id}` not found."
            )
            return

        self._conversation = conv
        container.remove_children()

        # Replay messages into the UI
        for msg in conv.messages:
            if msg.is_ai:
                msg_box = Vertical(classes="msg-box")
                header = Static(
                    f"\u2726 {msg.sender}",
                    classes="msg-sender msg-sender-ai",
                )
                content = Markdown(msg.content, classes="msg-content")
                container.mount(msg_box)
                msg_box.mount(header)
                msg_box.mount(content)
            else:
                self._add_user_message(container, msg.content)

        self._add_system_message(
            container,
            f"Loaded conversation: **{conv.title}** ({len(conv.messages)} messages)",
        )

    def _cmd_status(self, container: VerticalScroll) -> None:
        """Show current session status."""
        if self._conversation:
            lines = [
                "**Session Status:**\n",
                f"- **Conversation:** {self._conversation.title}",
                f"- **Status:** {self._conversation.status}",
                f"- **Messages:** {len(self._conversation.messages)}",
                f"- **Tokens:** {self._total_tokens:,}",
            ]
            if self._conversation.participants:
                lines.append(f"- **Participants:** {', '.join(self._conversation.participants)}")
        else:
            lines = [
                "**Session Status:**\n",
                "- No active conversation",
                f"- **Tokens:** {self._total_tokens:,}",
                "- Type a message to start",
            ]
        self._add_system_message(container, "\n".join(lines))

    def _cmd_export(self, container: VerticalScroll) -> None:
        """Export current conversation as markdown."""
        if not self._conversation or not self._conversation.messages:
            self._add_system_message(container, "Nothing to export.")
            return
        lines = [f"# {self._conversation.title}\n"]
        for msg in self._conversation.messages:
            ts = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            lines.append(f"**{msg.sender}** ({ts}):\n\n{msg.content}\n\n---\n")
        self._add_system_message(container, "\n".join(lines))

    def _cmd_config(self, container: VerticalScroll) -> None:
        """Show current configuration."""
        config = self._config_mgr.config
        if config is None:
            self._add_system_message(container, "No configuration loaded.")
            return
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
        self._add_system_message(container, "\n".join(lines))

    async def _cmd_connectors(self, container: VerticalScroll) -> None:
        """List all connector statuses."""
        if self._client is None:
            self._add_system_message(container, "Client not connected.")
            return
        connectors = await self._client.list_connectors()
        if connectors:
            lines = ["**Connectors:**\n"]
            for c in connectors:
                status = "\u2713" if c.configured else "\u2717"
                provider = f" ({c.provider})" if c.provider else ""
                lines.append(
                    f"- {status} **{c.name}**{provider} — {c.category}"
                )
            self._add_system_message(container, "\n".join(lines))
        else:
            self._add_system_message(container, "No connectors available.")

    async def _cmd_setup(self) -> None:
        """Re-run the setup wizard."""
        from firefly_dworkers_cli.tui.screens.setup import SetupScreen

        await self.push_screen(
            SetupScreen(self._config_mgr),
            callback=self._on_setup_complete,
        )

    # ── Project commands ──────────────────────────────────────

    async def _cmd_project(self, container: VerticalScroll, brief: str) -> None:
        """Run a multi-worker project from a brief."""
        if self._client is None:
            self._add_system_message(container, "Client not connected.")
            return

        self._add_system_message(
            container,
            f"Starting project: **{brief[:60]}{'...' if len(brief) > 60 else ''}**",
        )

        content_widget = Markdown("", classes="msg-content")
        msg_box = Vertical(classes="msg-box")
        header = Static(
            "\u2726 Project Orchestrator",
            classes="msg-sender msg-sender-ai",
        )
        await container.mount(msg_box)
        await msg_box.mount(header)
        await msg_box.mount(content_widget)

        indicator = Static(
            "\u25cf\u25cf\u25cf orchestrating...", classes="streaming-indicator"
        )
        await msg_box.mount(indicator)
        container.scroll_end(animate=False)

        tokens: list[str] = []
        self._is_streaming = True
        try:
            async for event in self._client.run_project(brief):
                if event.type in ("project_start", "project_complete"):
                    tokens.append(f"\n**{event.type}:** {event.content}\n")
                elif event.type == "task_assigned":
                    tokens.append(f"\n> Task assigned: {event.content}\n")
                elif event.type == "task_complete":
                    tokens.append(f"\n> Task complete: {event.content}\n")
                elif event.type in ("token", "complete"):
                    tokens.append(event.content)
                elif event.type == "error":
                    tokens.append(f"\n\n**Error:** {event.content}")
                else:
                    tokens.append(f"\n{event.content}")
                await content_widget.update("".join(tokens))
                container.scroll_end(animate=False)
        except Exception as e:
            tokens.append(f"\n\n**Error:** {e}")
            await content_widget.update("".join(tokens))
        finally:
            self._is_streaming = False
            indicator.remove()

    # ── Messaging commands ────────────────────────────────────

    def _get_messaging_tool(self, tool_name: str):
        """Create a messaging tool instance from the config."""
        config = self._config_mgr.config
        if config is None:
            return None

        try:
            from firefly_dworkers.tools.registry import tool_registry
        except ImportError:
            return None

        if not tool_registry.has(tool_name):
            return None

        # Get connector config for this tool
        connector_cfg = getattr(config.connectors, tool_name, None)
        if connector_cfg is None:
            return None

        # Build kwargs from connector config
        kwargs = connector_cfg.model_dump(exclude={"enabled", "provider", "credential_ref", "timeout"})
        kwargs = {k: v for k, v in kwargs.items() if v}  # filter empty
        return tool_registry.create(tool_name, **kwargs)

    async def _cmd_send(self, container: VerticalScroll, arg: str) -> None:
        """Send a message via a messaging tool.

        Usage: /send <tool> <channel> <message>
        Example: /send slack #general Hello from dworkers!
        """
        parts = arg.split(maxsplit=2)
        if len(parts) < 3:
            self._add_system_message(
                container,
                "Usage: `/send <tool> <channel> <message>`\n\n"
                "Examples:\n"
                "- `/send slack #general Hello!`\n"
                "- `/send teams general Check this out`\n"
                "- `/send email user@example.com Report attached`",
            )
            return

        tool_name, channel, message = parts
        tool = self._get_messaging_tool(tool_name)
        if tool is None:
            self._add_system_message(
                container,
                f"Messaging tool `{tool_name}` is not configured.\n\n"
                "Available: slack, teams, email.\n"
                "Configure via `~/.dworkers/config.yaml` or run `/setup`.",
            )
            return

        self._add_system_message(
            container, f"Sending via **{tool_name}** to `{channel}`..."
        )
        try:
            result = await tool.execute(
                action="send", channel=channel, content=message
            )
            msg_id = result.get("id", "unknown")
            self._add_system_message(
                container,
                f"Message sent successfully (id: `{msg_id}`)",
            )
        except Exception as e:
            self._add_system_message(
                container, f"**Error sending message:** {e}"
            )

    async def _cmd_channels(self, container: VerticalScroll, arg: str) -> None:
        """List channels for a messaging tool.

        Usage: /channels <tool>
        Example: /channels slack
        """
        tool_name = arg.strip()
        if not tool_name:
            self._add_system_message(
                container,
                "Usage: `/channels <tool>`\n\n"
                "Examples:\n"
                "- `/channels slack`\n"
                "- `/channels teams`\n"
                "- `/channels email`",
            )
            return

        tool = self._get_messaging_tool(tool_name)
        if tool is None:
            self._add_system_message(
                container,
                f"Messaging tool `{tool_name}` is not configured.\n\n"
                "Configure via `~/.dworkers/config.yaml` or run `/setup`.",
            )
            return

        try:
            result = await tool.execute(action="list_channels")
            channels = result.get("channels", [])
            if channels:
                lines = [f"**{tool_name.title()} Channels:**\n"]
                for ch in channels:
                    lines.append(f"- `{ch}`")
                self._add_system_message(container, "\n".join(lines))
            else:
                self._add_system_message(
                    container, f"No channels found for {tool_name}."
                )
        except Exception as e:
            self._add_system_message(
                container, f"**Error listing channels:** {e}"
            )

    # ── Actions ──────────────────────────────────────────────

    def action_new_conversation(self) -> None:
        """Start a new conversation."""
        self._conversation = None
        message_list = self.query_one("#message-list", VerticalScroll)
        message_list.remove_children()
        self._add_system_message(
            message_list,
            "Started a new conversation. Type a message to begin.",
        )

    def action_focus_input(self) -> None:
        """Focus the input area."""
        self.query_one("#prompt-input", TextArea).focus()
