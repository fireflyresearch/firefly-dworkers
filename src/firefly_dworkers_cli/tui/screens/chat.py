"""Chat screen — full conversation view with streaming messages."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.backend.models import ChatMessage, Conversation
from firefly_dworkers_cli.tui.backend.store import ConversationStore
from firefly_dworkers_cli.tui.widgets.input_bar import InputBar
from firefly_dworkers_cli.tui.widgets.message_bubble import MessageBubble
from firefly_dworkers_cli.tui.widgets.message_list import MessageList
from firefly_dworkers_cli.tui.widgets.status_badge import StatusBadge
from firefly_dworkers_cli.tui.widgets.streaming_bubble import StreamingBubble

# Known worker roles for @mention detection.
_KNOWN_ROLES = {"analyst", "researcher", "data_analyst", "manager", "designer"}

# Regex to find @mention patterns.
_MENTION_RE = re.compile(r"@(\w+)")


class ChatHeader(Horizontal):
    """Title bar showing conversation title, tags, and status."""

    DEFAULT_CSS = """
    ChatHeader {
        height: 3;
        background: #181825;
        border-bottom: solid #313244;
        padding: 0 2;
        align: left middle;
    }

    ChatHeader .chat-title {
        width: auto;
        text-style: bold;
        padding: 0 1;
    }

    ChatHeader .chat-tag {
        width: auto;
        margin: 0 1;
    }

    ChatHeader .chat-status {
        dock: right;
        width: auto;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        title: str = "New Conversation",
        tags: list[str] | None = None,
        status: str = "active",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._tags = tags or []
        self._status = status

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="chat-title")
        for tag in self._tags:
            yield StatusBadge(tag, variant="default", classes="chat-tag")
        variant = "success" if self._status == "active" else "default"
        yield StatusBadge(self._status, variant=variant, classes="chat-status")


class ChatScreen(Vertical):
    """Full conversation view with message history, streaming, and commands."""

    DEFAULT_CSS = """
    ChatScreen {
        height: 1fr;
        width: 1fr;
    }
    """

    def __init__(
        self,
        conversation: Conversation | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._conversation = conversation
        self._store = ConversationStore()
        self._client: DworkersClient | None = None

    def compose(self) -> ComposeResult:
        title = self._conversation.title if self._conversation else "New Conversation"
        tags = self._conversation.tags if self._conversation else []
        status = self._conversation.status if self._conversation else "active"

        yield ChatHeader(title=title, tags=tags, status=status)
        yield MessageList()
        yield InputBar()

    async def on_mount(self) -> None:
        self._client = await create_client()
        if self._conversation is not None:
            self._load_history()

    def _load_history(self) -> None:
        """Render existing messages from the conversation as MessageBubble widgets."""
        if self._conversation is None:
            return
        message_list = self.query_one(MessageList)
        for msg in self._conversation.messages:
            bubble = MessageBubble(
                sender=msg.sender,
                content=msg.content,
                timestamp=msg.timestamp,
                is_ai=msg.is_ai,
                role=msg.role,
                status=msg.status,
            )
            message_list.add_message(bubble)

    async def on_input_bar_submitted(self, event: InputBar.Submitted) -> None:
        """Handle input submission — slash commands or regular messages."""
        text = event.text.strip()
        if not text:
            return

        if text.startswith("/"):
            await self._handle_slash_command(text)
        else:
            await self._send_message(text)

    async def _send_message(self, text: str) -> None:
        """Send a user message and stream the agent response."""
        # Ensure we have a conversation.
        if self._conversation is None:
            title = text[:50] + ("..." if len(text) > 50 else "")
            self._conversation = self._store.create_conversation(title)

        message_list = self.query_one(MessageList)

        # Create and display the user message.
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

        user_bubble = MessageBubble(
            sender="You",
            content=text,
            timestamp=user_msg.timestamp,
            is_ai=False,
        )
        message_list.add_message(user_bubble)

        # Determine the target worker role from @mentions.
        role = self._extract_role(text) or "analyst"
        sender_name = role.replace("_", " ").title()

        # Create streaming bubble for agent response.
        streaming = StreamingBubble(sender=sender_name, role=role)
        message_list.add_message(streaming)

        # Stream from the client.
        if self._client is not None:
            async for event in await self._client.run_worker(
                role,
                text,
                conversation_id=self._conversation.id,
            ):
                if event.type == "token" or event.type == "complete":
                    streaming.append_token(event.content)
                elif event.type == "error":
                    streaming.append_token(f"\n\n**Error:** {event.content}")

        # Finalize the streaming bubble.
        final_bubble = streaming.finalize()
        message_list.replace_streaming(streaming, final_bubble)

        # Save the agent message.
        agent_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            conversation_id=self._conversation.id,
            role=role,
            sender=sender_name,
            content=streaming.full_content,
            timestamp=datetime.now(UTC),
            is_ai=True,
        )
        self._store.add_message(self._conversation.id, agent_msg)

    def _extract_role(self, text: str) -> str | None:
        """Check for @analyst, @researcher, etc. in the message text."""
        match = _MENTION_RE.search(text)
        if match:
            mention = match.group(1).lower()
            if mention in _KNOWN_ROLES:
                return mention
        return None

    async def _handle_slash_command(self, text: str) -> None:
        """Handle slash commands: /team, /plan, /status, /export."""
        message_list = self.query_one(MessageList)
        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        _arg = parts[1] if len(parts) > 1 else ""

        match command:
            case "/team":
                if self._client is not None:
                    workers = await self._client.list_workers()
                    lines = ["**Team Members:**"]
                    for w in workers:
                        status = "enabled" if w.enabled else "disabled"
                        lines.append(f"- **{w.name}** ({w.role}) [{status}]")
                    content = "\n".join(lines)
                else:
                    content = "Client not available."
                bubble = MessageBubble(
                    sender="System",
                    content=content,
                    timestamp=datetime.now(UTC),
                    is_ai=True,
                    role="system",
                )
                message_list.add_message(bubble)

            case "/plan":
                if self._client is not None:
                    plans = await self._client.list_plans()
                    if plans:
                        lines = ["**Available Plans:**"]
                        for p in plans:
                            roles = ", ".join(p.worker_roles) if p.worker_roles else "none"
                            lines.append(
                                f"- **{p.name}** ({p.steps} steps) — workers: {roles}"
                            )
                        content = "\n".join(lines)
                    else:
                        content = "No plans available."
                else:
                    content = "Client not available."
                bubble = MessageBubble(
                    sender="System",
                    content=content,
                    timestamp=datetime.now(UTC),
                    is_ai=True,
                    role="system",
                )
                message_list.add_message(bubble)

            case "/status":
                if self._conversation:
                    msg_count = len(self._conversation.messages)
                    content = (
                        f"**Conversation:** {self._conversation.title}\n"
                        f"**Status:** {self._conversation.status}\n"
                        f"**Messages:** {msg_count}\n"
                        f"**Participants:** {', '.join(self._conversation.participants) or 'none'}"
                    )
                else:
                    content = "No active conversation."
                bubble = MessageBubble(
                    sender="System",
                    content=content,
                    timestamp=datetime.now(UTC),
                    is_ai=True,
                    role="system",
                )
                message_list.add_message(bubble)

            case "/export":
                if self._conversation and self._conversation.messages:
                    lines = [f"# {self._conversation.title}\n"]
                    for msg in self._conversation.messages:
                        ts = msg.timestamp.strftime("%Y-%m-%d %H:%M")
                        lines.append(f"**{msg.sender}** ({ts}):\n{msg.content}\n")
                    content = "Export:\n\n" + "\n".join(lines)
                else:
                    content = "Nothing to export."
                bubble = MessageBubble(
                    sender="System",
                    content=content,
                    timestamp=datetime.now(UTC),
                    is_ai=True,
                    role="system",
                )
                message_list.add_message(bubble)

            case _:
                bubble = MessageBubble(
                    sender="System",
                    content=f"Unknown command: `{command}`\n\nAvailable: /team, /plan, /status, /export",
                    timestamp=datetime.now(UTC),
                    is_ai=True,
                    role="system",
                )
                message_list.add_message(bubble)

    async def _execute_plan(self, plan_name: str) -> None:
        """Stream execution output for a named plan."""
        if self._client is None:
            return

        message_list = self.query_one(MessageList)
        message_list.add_divider(f"Executing plan: {plan_name}")

        streaming = StreamingBubble(sender="Planner", role="planner")
        message_list.add_message(streaming)

        async for event in await self._client.execute_plan(plan_name):
            if event.type == "token" or event.type == "complete":
                streaming.append_token(event.content)
            elif event.type == "error":
                streaming.append_token(f"\n\n**Error:** {event.content}")

        final_bubble = streaming.finalize()
        message_list.replace_streaming(streaming, final_bubble)
