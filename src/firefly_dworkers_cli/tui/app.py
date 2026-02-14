"""DworkersApp — chat-first TUI matching Claude Code's terminal experience.

The entire app is a single chat view: messages scroll upward, input is
docked at the bottom, and a status bar shows model/connection info.
All features (settings, team, plans, etc.) are accessible via slash commands.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Markdown, Static, TextArea

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
    /status        Current session info
    /export        Export conversation
    /new           Start a new conversation
    /quit          Exit
"""

_HELP_TEXT = """\
Available commands:
  /help            Show this help message
  /team            List available AI workers and their status
  /plan            List available workflow plans
  /plan <name>     Execute a named plan
  /conversations   List all saved conversations
  /new             Start a fresh conversation
  /status          Show current session status
  /export          Export current conversation as markdown
  /quit            Exit dworkers

Tips:
  - Use @analyst, @researcher, @data_analyst, @manager, @designer
    to route your message to a specific worker role
  - Default worker is @analyst if no role is specified
  - Messages support markdown formatting
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
        """Connect to backend and focus input."""
        self._client = await create_client()

        # Update connection status
        conn = self.query_one("#conn-status", Static)
        client_type = type(self._client).__name__
        if client_type == "RemoteClient":
            conn.update("\u25cf remote")
            model_label = self.query_one(".status-model", Static)
            model_label.update("remote")
        else:
            conn.update("\u25cf local")

        # Focus the input
        self.query_one("#prompt-input", TextArea).focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Auto-grow the text area as user types."""
        pass  # TextArea handles this naturally

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

        if self._client is not None:
            try:
                async for event in await self._client.run_worker(
                    role,
                    text,
                    conversation_id=self._conversation.id,
                ):
                    if event.type in ("token", "complete"):
                        tokens.append(event.content)
                        await content_widget.update("".join(tokens))
                        message_list.scroll_end(animate=False)
                    elif event.type == "tool_call":
                        # Show tool call box
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
        """Check for @analyst, @researcher, etc. in the message text."""
        match = _MENTION_RE.search(text)
        if match:
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

            case "/conversations":
                self._cmd_conversations(message_list)

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

            case "/export":
                self._cmd_export(message_list)

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
            async for event in await self._client.execute_plan(plan_name):
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
