"""DworkersApp — chat-first TUI matching Claude Code's terminal experience.

The entire app is a single chat view: messages scroll upward, input is
docked at the bottom, and a status bar shows model/connection info.
All features (settings, team, plans, etc.) are accessible via slash commands.

On first run (or when no usable config exists), the app launches a setup
wizard to configure the LLM provider and API keys.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
import re
import time
import uuid
from datetime import UTC, datetime

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import Markdown, Static, TextArea

from firefly_dworkers_cli.config import ConfigManager
from firefly_dworkers_cli.tui.backend.client import DworkersClient, create_client
from firefly_dworkers_cli.tui.backend.models import (
    EXTENSION_MIME_MAP,
    MAX_ATTACHMENT_SIZE,
    MAX_ATTACHMENTS,
    ChatMessage,
    Conversation,
    FileAttachment,
    WorkerInfo,
)
from firefly_dworkers_cli.tui.backend.store import ConversationStore
from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler
from firefly_dworkers_cli.tui.commands import CommandRouter
from firefly_dworkers_cli.tui.response_timer import ResponseTimer
from firefly_dworkers_cli.tui.theme import APP_CSS
from firefly_dworkers_cli.tui.widgets.thinking_indicator import ThinkingIndicator

# Fallback roles used before the backend has been queried.
_FALLBACK_ROLES = {"analyst", "researcher", "data_analyst", "manager", "designer"}
_MENTION_RE = re.compile(r"@(\w+)")

# Streaming timeout in seconds (5 minutes).
_STREAMING_TIMEOUT = 300


_PALETTE_COMMANDS = [
    ("help", "Show available commands"),
    ("team", "List available AI workers"),
    ("invite", "Invite a worker to the conversation"),
    ("private", "Start/end private conversation"),
    ("plan", "List or execute workflow plans"),
    ("project", "Run a multi-worker project"),
    ("attach", "Attach a file to the next message"),
    ("detach", "Clear file attachments"),
    ("status", "Show session status"),
    ("config", "Show current configuration"),
    ("new", "Start a new conversation"),
    ("conversations", "List saved conversations"),
    ("models", "Show available models"),
    ("model", "Switch default model"),
    ("autonomy", "View or change autonomy level"),
    ("connectors", "List connector statuses"),
    ("usage", "Show usage statistics"),
    ("export", "Export conversation as markdown"),
    ("list", "List recent conversations"),
    ("search", "Search conversation messages"),
    ("rename", "Rename the current conversation"),
    ("archive", "Archive the current conversation"),
    ("clear", "Clear chat display"),
    ("setup", "Re-run setup wizard"),
    ("quit", "Exit dworkers"),
]


class MentionPopup(Vertical):
    """Autocomplete popup for @mentions, showing matching worker roles."""

    def __init__(self, items: list[tuple[str, str]]) -> None:
        super().__init__(id="mention-popup")
        self._items = items  # [(role, description), ...]
        self._selected = 0

    def compose(self) -> ComposeResult:
        for i, (role, desc) in enumerate(self._items):
            label = f"@{role}  {desc}" if desc else f"@{role}"
            cls = "mention-item-selected" if i == 0 else "mention-item"
            yield Static(label, classes=cls, id=f"mention-{i}")

    def move(self, delta: int) -> None:
        """Move selection by *delta* (-1 = up, +1 = down)."""
        if not self._items:
            return
        old = self._selected
        self._selected = max(0, min(len(self._items) - 1, self._selected + delta))
        if old != self._selected:
            with contextlib.suppress(NoMatches):
                self.query_one(f"#mention-{old}", Static).set_classes("mention-item")
                self.query_one(f"#mention-{self._selected}", Static).set_classes("mention-item-selected")

    @property
    def selected_role(self) -> str | None:
        if self._items:
            return self._items[self._selected][0]
        return None


class CommandPopup(Vertical):
    """Autocomplete popup for /slash commands."""

    def __init__(self, items: list[tuple[str, str]]) -> None:
        super().__init__(id="command-popup")
        self._items = items
        self._selected = 0

    def compose(self) -> ComposeResult:
        for i, (cmd, desc) in enumerate(self._items):
            label = f"/{cmd}  {desc}"
            cls = "command-item-selected" if i == 0 else "command-item"
            yield Static(label, classes=cls, id=f"cmd-{i}")

    def move(self, delta: int) -> None:
        """Move selection by *delta* (-1 = up, +1 = down)."""
        if not self._items:
            return
        old = self._selected
        self._selected = max(0, min(len(self._items) - 1, self._selected + delta))
        if old != self._selected:
            with contextlib.suppress(NoMatches):
                self.query_one(f"#cmd-{old}", Static).set_classes("command-item")
                self.query_one(f"#cmd-{self._selected}", Static).set_classes(
                    "command-item-selected"
                )

    @property
    def selected_command(self) -> str | None:
        if self._items:
            return self._items[self._selected][0]
        return None


class PromptInput(TextArea):
    """Chat input — Enter submits, Shift+Enter inserts newline.

    TextArea's internal ``_on_key`` consumes Enter (inserts newline) and
    calls ``event.stop()``, so the key never bubbles to the App.  This
    subclass intercepts Enter *before* the parent handler, posts a
    :class:`Submitted` message, and lets the App handle it.

    Also provides @mention and /command autocomplete when the user types
    ``@`` or ``/`` followed by characters. The popups are managed by the
    parent :class:`DworkersApp`.
    """

    class Submitted(Message):
        """Posted when the user presses Enter with non-empty text."""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    async def _on_key(self, event: events.Key) -> None:
        # If command popup is visible, intercept navigation keys.
        cmd_popup = self._get_command_popup()
        if cmd_popup is not None:
            if event.key == "escape":
                self.app._dismiss_command_popup()
                event.stop()
                event.prevent_default()
                return
            if event.key in ("up", "down"):
                cmd_popup.move(-1 if event.key == "up" else 1)
                event.stop()
                event.prevent_default()
                return
            if event.key in ("tab", "enter"):
                cmd = cmd_popup.selected_command
                if cmd:
                    self.app._complete_command(cmd)
                event.stop()
                event.prevent_default()
                return

        # If mention popup is visible, intercept navigation keys.
        popup = self._get_mention_popup()
        if popup is not None:
            if event.key == "escape":
                self.app._dismiss_mention_popup()
                event.stop()
                event.prevent_default()
                return
            if event.key in ("up", "down"):
                popup.move(-1 if event.key == "up" else 1)
                event.stop()
                event.prevent_default()
                return
            if event.key in ("tab", "enter"):
                role = popup.selected_role
                if role:
                    self.app._complete_mention(role)
                event.stop()
                event.prevent_default()
                return

        if event.key == "enter":
            text = self.text.strip()
            if text:
                self.post_message(self.Submitted(text))
                self.clear()
            event.stop()
            event.prevent_default()
            return
        if event.key == "shift+enter":
            # Insert a newline (what Enter normally does in TextArea)
            start, end = self.selection
            self._replace_via_keyboard("\n", start, end)
            event.stop()
            event.prevent_default()
            return
        await super()._on_key(event)

    def _get_mention_popup(self) -> MentionPopup | None:
        """Return the active mention popup, or None."""
        try:
            return self.app.query_one("#mention-popup", MentionPopup)
        except NoMatches:
            return None

    def _get_command_popup(self) -> CommandPopup | None:
        """Return the active command popup, or None."""
        try:
            return self.app.query_one("#command-popup", CommandPopup)
        except NoMatches:
            return None


class SlashCommandProvider(Provider):
    """Slash commands for the Textual command palette (Ctrl+P)."""

    async def discover(self) -> Hits:
        total = len(_PALETTE_COMMANDS)
        for i, (name, desc) in enumerate(_PALETTE_COMMANDS):
            yield Hit(
                1.0 - i * (0.5 / total),
                f"/{name}",
                self._make_command(name),
                help=desc,
            )

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for name, desc in _PALETTE_COMMANDS:
            score = matcher.match(f"{name} {desc}")
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(f"/{name}"),
                    self._make_command(name),
                    help=desc,
                )

    def _make_command(self, name: str):
        async def callback() -> None:
            await self.app._handle_input(f"/{name}")
        return callback


def _get_slash_commands() -> type[SlashCommandProvider]:
    return SlashCommandProvider


class DworkersApp(App):
    """Chat-first TUI for dworkers — inspired by Claude Code."""

    TITLE = "dworkers"
    CSS = APP_CSS
    COMMANDS = App.COMMANDS | {_get_slash_commands}

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("ctrl+c", "cancel_or_quit", "Cancel/Quit", show=False),
        Binding("ctrl+n", "new_conversation", "New Chat", show=False),
        Binding("ctrl+l", "clear_chat", "Clear", show=False),
        Binding("escape", "focus_input", "Focus Input", show=False),
    ]

    def __init__(
        self,
        *,
        mode: str = "auto",
        autonomy_override: str | None = None,
        server_url: str | None = None,
    ) -> None:
        super().__init__()
        self._mode = mode
        self._autonomy_override = autonomy_override
        self._server_url = server_url
        self._config_mgr = ConfigManager()
        self._store = ConversationStore()
        self._client: DworkersClient | None = None
        self._conversation: Conversation | None = None
        self._total_tokens = 0
        self._is_streaming = False
        self._cancel_streaming = asyncio.Event()
        self._router = CommandRouter(
            client=None, store=self._store, config_mgr=self._config_mgr,
        )
        self._checkpoint_handler = TUICheckpointHandler()
        self._router.checkpoint_handler = self._checkpoint_handler
        self._last_ctrl_c: float = 0.0
        self._config_load_failed: bool = False
        # Dynamic worker cache — populated after backend connects.
        self._worker_cache: list[WorkerInfo] = []
        self._known_roles: set[str] = set(_FALLBACK_ROLES)
        self._role_descriptions: dict[str, str] = {}
        self._name_to_role: dict[str, str] = {}
        # Private conversation mode — when set, all messages go to this role.
        self._private_role: str | None = None
        # File attachments for the next message.
        self._attachments: list[FileAttachment] = []
        self._compaction_summary: str = ""
        if self._autonomy_override:
            self._router.autonomy_level = self._autonomy_override

    def _save_session_state(self) -> None:
        """Persist session state to SQLite for resumption."""
        state: dict[str, str] = {}
        if self._conversation:
            state["active_conversation_id"] = self._conversation.id
        state["total_tokens"] = str(self._total_tokens)
        if self._private_role:
            state["private_role"] = self._private_role
        self._store.save_session_state(state)

    async def _restore_session_state(self) -> None:
        """Restore session state from SQLite."""
        state = self._store.load_session_state()
        conv_id = state.get("active_conversation_id", "")
        if conv_id:
            conv = self._store.get_conversation(conv_id)
            if conv:
                self._conversation = conv
        self._total_tokens = int(state.get("total_tokens", "0"))
        self._private_role = state.get("private_role") or None

    def compose(self) -> ComposeResult:
        # Header bar
        with Horizontal(id="header-bar"):
            yield Static("dworkers", classes="header-title")
            yield Static("Ctrl+P commands · Ctrl+N new · Ctrl+L clear · Ctrl+Q quit", classes="header-hint")

        # Welcome banner (shown initially, hidden once chat starts)
        with Vertical(id="welcome"):
            yield Static(CommandRouter.WELCOME_TEXT, classes="welcome-text")

        # Message list (hidden initially, shown once chat starts)
        yield VerticalScroll(id="message-list")

        # Input area
        with Vertical(id="input-area"):
            yield Static("", id="attachment-bar")
            with Horizontal(id="input-row"):
                yield Static("> ", classes="prompt-prefix", id="prompt-prefix")
                yield PromptInput(id="prompt-input")
            yield Static("Enter to send · Shift+Enter for newline · /help for commands",
                         classes="input-hint", id="input-hint")

        # Status bar — model · model-location · autonomy · participants · tokens (right: connection)
        with Horizontal(id="status-bar"):
            yield Static("local", classes="status-item status-model", id="status-model")
            yield Static(" · ", classes="status-sep", id="sep-after-model")
            yield Static("\u2601 cloud", classes="status-item status-model-loc", id="status-model-loc")
            yield Static(" · ", classes="status-sep", id="sep-after-model-loc")
            yield Static("\u25cf", classes="status-item autonomy-semi-supervised", id="autonomy-dot")
            yield Static(" semi-supervised", classes="status-item status-autonomy", id="status-autonomy")
            yield Static("", classes="status-item status-private", id="status-private")
            yield Static("", classes="status-item status-participants", id="status-participants")
            yield Static("", classes="status-item status-tokens", id="token-count")
            yield Static("", classes="status-connection status-connected", id="conn-status")

    async def on_mount(self) -> None:
        """Load config, optionally run setup wizard, then connect to backend."""
        # Check if setup is needed
        if self._config_mgr.needs_setup():
            from firefly_dworkers_cli.tui.screens.setup import SetupWizard

            await self.push_screen(
                SetupWizard(self._config_mgr),
                callback=self._on_setup_complete,
            )
        else:
            # Load existing config and register in tenant_registry
            try:
                config = self._config_mgr.load()
                self._update_model_label(config.models.default)
            except Exception:
                self._config_load_failed = True
            await self._connect_and_focus()

    def _on_setup_complete(self, result: object) -> None:
        """Callback when setup wizard finishes."""
        if result is not None and hasattr(result, "models"):
            self._update_model_label(result.models.default)
        self._update_status_bar()
        self.call_after_refresh(self._connect_and_focus)

    # Providers whose models run locally (on-device).
    _LOCAL_MODEL_PROVIDERS = {"ollama", "llamacpp", "llama.cpp", "lmstudio", "local", "gguf"}

    def _update_model_label(self, model_string: str) -> None:
        """Update the status bar model label and local/cloud indicator."""
        with contextlib.suppress(NoMatches):
            if ":" in model_string:
                provider, model_name = model_string.split(":", 1)
            else:
                provider, model_name = "", model_string
            self.query_one("#status-model", Static).update(model_name)

            # Determine if model is local or cloud.
            is_local_model = provider.lower() in self._LOCAL_MODEL_PROVIDERS
            loc_widget = self.query_one("#status-model-loc", Static)
            if is_local_model:
                loc_widget.update("\u2302 local model")
                for cls in list(loc_widget.classes):
                    if cls.startswith("model-loc-"):
                        loc_widget.remove_class(cls)
                loc_widget.add_class("model-loc-local")
            else:
                loc_widget.update("\u2601 cloud model")
                for cls in list(loc_widget.classes):
                    if cls.startswith("model-loc-"):
                        loc_widget.remove_class(cls)
                loc_widget.add_class("model-loc-cloud")

    # Mapping from autonomy level to CSS class suffix.
    _AUTONOMY_CSS_MAP: dict[str, str] = {
        "autonomous": "autonomy-autonomous",
        "semi_supervised": "autonomy-semi-supervised",
        "manual": "autonomy-manual",
    }

    def _update_autonomy_display(self) -> None:
        """Set the autonomy dot color based on the current level."""
        autonomy = self._router.autonomy_level
        css_class = self._AUTONOMY_CSS_MAP.get(autonomy, "autonomy-semi-supervised")
        with contextlib.suppress(NoMatches):
            dot = self.query_one("#autonomy-dot", Static)
            # Remove all autonomy-* classes and set the correct one
            for cls in list(dot.classes):
                if cls.startswith("autonomy-"):
                    dot.remove_class(cls)
            dot.add_class(css_class)

    def _update_status_bar(self) -> None:
        """Refresh all status bar items after state changes."""
        # Autonomy
        autonomy = self._router.autonomy_level
        display = autonomy.replace("_", "-")
        with contextlib.suppress(NoMatches):
            self.query_one("#status-autonomy", Static).update(f" {display}")
        self._update_autonomy_display()
        self._update_participants_display()

    def _update_participants_display(self) -> None:
        """Update the participants indicator in the status bar."""
        with contextlib.suppress(NoMatches):
            # Private mode indicator
            private_widget = self.query_one("#status-private", Static)
            if self._private_role:
                private_widget.update(f" · [private: @{self._private_role}]")
            else:
                private_widget.update("")

            # Participants list (agent roles active in the conversation).
            parts_widget = self.query_one("#status-participants", Static)
            if self._conversation and self._conversation.participants:
                agent_roles = [
                    p for p in self._conversation.participants if p != "user"
                ]
                if agent_roles:
                    parts_widget.update(
                        " · " + " ".join(f"@{r}" for r in agent_roles)
                    )
                else:
                    parts_widget.update("")
            else:
                parts_widget.update("")

    async def _connect_and_focus(self) -> None:
        """Connect to backend client and focus the input."""
        self._client = await create_client(
            mode=self._mode,
            server_url=self._server_url,
            checkpoint_handler=self._checkpoint_handler,
        )
        self._router.client = self._client

        # Update connection status — shows whether dworkers backend is local or remote.
        conn = self.query_one("#conn-status", Static)
        client_type = type(self._client).__name__
        if client_type == "RemoteClient":
            conn.update("\u25cf remote server")
            conn.remove_class("status-connected")
            conn.add_class("status-remote")
        else:
            conn.update("\u25cf local server")

        # Cache available workers for autocomplete and mention detection.
        await self._refresh_workers()

        # Focus the input
        self.query_one("#prompt-input", PromptInput).focus()
        self._update_status_bar()

        # Show config load error if it occurred
        if self._config_load_failed:
            self._config_load_failed = False
            self._hide_welcome()
            message_list = self.query_one("#message-list", VerticalScroll)
            await self._add_system_message(
                message_list,
                "**Warning:** Config file could not be loaded. Run `/setup` to reconfigure.",
            )

    # ── @mention autocomplete ────────────────────────────────

    # Regex to find an @mention fragment at the end of the current text.
    _MENTION_PARTIAL_RE = re.compile(r"@(\w*)$")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update the input hint and manage popup autocomplete as the user types."""
        if event.text_area.id != "prompt-input":
            return
        text = event.text_area.text
        self._update_input_hint(text)
        self._update_mention_popup(text)
        self._update_command_popup(text)

    def _update_mention_popup(self, text: str) -> None:
        """Show, update, or dismiss the @mention autocomplete popup."""
        match = self._MENTION_PARTIAL_RE.search(text)
        if match is None:
            self._dismiss_mention_popup()
            return

        fragment = match.group(1).lower()

        if self._worker_cache:
            # Name entries first: @amara  Manager — Your team lead
            name_matches: list[tuple[str, str]] = []
            role_matches: list[tuple[str, str]] = []
            for w in self._worker_cache:
                if w.name:
                    lower_name = w.name.lower()
                    if lower_name.startswith(fragment):
                        role_title = w.role.replace("_", " ").title()
                        desc = f"{role_title} — {w.description}" if w.description else role_title
                        name_matches.append((lower_name, desc))
                if w.role.startswith(fragment):
                    name_label = w.name if w.name else ""
                    desc = f"{name_label} — {w.description}" if w.description and name_label else (name_label or w.description or "")
                    role_matches.append((w.role, desc))
            matches = name_matches + role_matches
        else:
            # Fallback if workers haven't loaded yet.
            matches = [
                (r, "") for r in sorted(_FALLBACK_ROLES) if r.startswith(fragment)
            ]

        if not matches:
            self._dismiss_mention_popup()
            return

        # Replace existing popup to reflect new filter.
        self._dismiss_mention_popup()
        popup = MentionPopup(matches)
        input_area = self.query_one("#input-area", Vertical)
        input_area.mount(popup, before=self.query_one("#input-row", Horizontal))

    def _dismiss_mention_popup(self) -> None:
        """Remove the mention popup if it exists."""
        with contextlib.suppress(NoMatches):
            self.query_one("#mention-popup", MentionPopup).remove()

    def _complete_mention(self, role: str) -> None:
        """Replace the partial @fragment with the completed @role."""
        self._dismiss_mention_popup()
        prompt = self.query_one("#prompt-input", PromptInput)
        text = prompt.text
        match = self._MENTION_PARTIAL_RE.search(text)
        if match:
            new_text = text[: match.start()] + f"@{role} "
            prompt.clear()
            prompt.insert(new_text)

    # ── /command autocomplete ─────────────────────────────────

    def _match_command_fragment(self, text: str) -> str | None:
        """Return the command fragment if text starts with / and has no space."""
        if not text.startswith("/"):
            return None
        if " " in text:
            return None
        return text[1:]

    def _update_command_popup(self, text: str) -> None:
        """Show, update, or dismiss the /command autocomplete popup."""
        fragment = self._match_command_fragment(text)
        if fragment is None:
            self._dismiss_command_popup()
            return

        matches = [
            (cmd, desc) for cmd, desc in _PALETTE_COMMANDS if cmd.startswith(fragment)
        ]
        if not matches:
            self._dismiss_command_popup()
            return

        # Replace existing popup to reflect new filter.
        self._dismiss_command_popup()
        popup = CommandPopup(matches[:10])
        input_area = self.query_one("#input-area", Vertical)
        input_area.mount(popup, before=self.query_one("#input-row", Horizontal))

    def _dismiss_command_popup(self) -> None:
        """Remove the command popup if it exists."""
        with contextlib.suppress(NoMatches):
            self.query_one("#command-popup", CommandPopup).remove()

    def _complete_command(self, cmd: str) -> None:
        """Replace the partial /fragment with the completed /command."""
        self._dismiss_command_popup()
        prompt = self.query_one("#prompt-input", PromptInput)
        prompt.clear()
        prompt.insert(f"/{cmd} ")

    async def on_prompt_input_submitted(self, event: PromptInput.Submitted) -> None:
        """Handle Enter-to-submit from the chat input."""
        if not self._is_streaming:
            await self._handle_input(event.text)

    async def on_key(self, event: events.Key) -> None:
        """Handle Escape to cancel streaming."""
        if event.key == "escape" and self._is_streaming:
            self._cancel_streaming.set()
            with contextlib.suppress(Exception):
                for ind in self.query(".streaming-indicator"):
                    ind.update("Cancelling...")
            event.prevent_default()
            event.stop()

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
        # Build metadata for attachment info (without raw data).
        msg_metadata: dict = {}
        if self._attachments:
            msg_metadata["attachments"] = [
                {"filename": a.filename, "size": a.size, "media_type": a.media_type}
                for a in self._attachments
            ]
        user_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            conversation_id=self._conversation.id,
            role="user",
            sender="You",
            content=text,
            timestamp=datetime.now(UTC),
            is_ai=False,
            metadata=msg_metadata,
        )
        self._store.add_message(self._conversation.id, user_msg)
        # Track participants
        if "user" not in self._conversation.participants:
            self._conversation.participants.append("user")
        await self._add_user_message(message_list, text)

        # Determine target worker role (private mode overrides @mentions).
        if self._private_role:
            role = self._private_role
        else:
            role = self._extract_role(text) or "manager"
        display_name, avatar, avatar_color = self._get_worker_display(role)
        sender_name = display_name
        sender_label = f"({avatar}) {display_name}" if avatar else display_name
        avatar_cls = f" avatar-{avatar_color}" if avatar_color else ""

        # Add AI response header
        ai_header = Static(
            sender_label,
            classes=f"msg-sender msg-sender-ai{avatar_cls}",
        )
        msg_box = Vertical(classes="msg-box-ai")
        await message_list.mount(msg_box)
        await msg_box.mount(ai_header)

        # Create streaming content
        content_widget = Markdown("", classes="msg-content")
        await msg_box.mount(content_widget)

        indicator = ThinkingIndicator()
        await msg_box.mount(indicator)
        message_list.scroll_end(animate=False)

        # Stream from client
        timer = ResponseTimer()
        timer.start()
        self._is_streaming = True
        tokens: list[str] = []
        first_token_marked = False
        last_render = 0.0

        try:
            if self._client is not None:
                try:
                    async with asyncio.timeout(_STREAMING_TIMEOUT):
                        # Pass pending attachments if any.
                        send_attachments = self._attachments or None
                        async for event in self._client.run_worker(
                            role,
                            text,
                            attachments=send_attachments,
                            conversation_id=self._conversation.id,
                        ):
                            if self._cancel_streaming.is_set():
                                tokens.append("\n\n_[Cancelled by user]_")
                                await content_widget.update("".join(tokens))
                                break
                            if event.type in ("token", "complete"):
                                if not first_token_marked:
                                    first_token_marked = True
                                    timer.mark_first_token()
                                    indicator.set_streaming_mode(timer)
                                tokens.append(event.content)
                                # Throttle: render at most every 80ms
                                now = time.monotonic()
                                if event.type == "complete" or now - last_render >= 0.08:
                                    last_render = now
                                    await content_widget.update("".join(tokens))
                                    if self._is_near_bottom(message_list):
                                        message_list.scroll_end(animate=False)
                            elif event.type == "tool_call":
                                tool_box = Vertical(classes="tool-call")
                                await msg_box.mount(tool_box)
                                await tool_box.mount(
                                    Static(f"\u2699 {event.content}", classes="tool-call-header")
                                )
                                if self._is_near_bottom(message_list):
                                    message_list.scroll_end(animate=False)
                            elif event.type == "error":
                                tokens.append(f"\n\n**Error:** {event.content}")
                                await content_widget.update("".join(tokens))
                except TimeoutError:
                    tokens.append("\n\n**Error:** Response timed out after 5 minutes.")
                    await content_widget.update("".join(tokens))
                except Exception as e:
                    tokens.append(f"\n\n**Error:** {e}")
                    await content_widget.update("".join(tokens))
        finally:
            timer.stop()
            self._is_streaming = False
            self._cancel_streaming.clear()
            indicator.stop()
            indicator.remove()

        # Final flush of any remaining unrendered tokens
        final_content = "".join(tokens)
        await content_widget.update(final_content)

        # Save agent message
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
        if role not in self._conversation.participants:
            self._conversation.participants.append(role)
        self._update_participants_display()

        # Update token count (rough estimate)
        token_estimate = self._estimate_tokens(final_content)
        self._total_tokens += token_estimate
        self.query_one("#token-count", Static).update(
            f" · ~{self._total_tokens:,} tokens"
        )

        # Response summary footer
        summary = Static(timer.format_summary(token_estimate), classes="response-summary")
        await msg_box.mount(summary)

        message_list.scroll_end(animate=False)
        # Clear attachments after sending.
        if self._attachments:
            self._clear_attachments()
        self._update_input_hint()

    async def _add_user_message(self, container: VerticalScroll, text: str) -> None:
        """Mount a user message into the message list."""
        msg_box = Vertical(classes="msg-box")
        header = Static("You", classes="msg-sender msg-sender-human")
        content = Markdown(text, classes="msg-content msg-content-user")
        await container.mount(msg_box)
        await msg_box.mount(header)
        await msg_box.mount(content)
        container.scroll_end(animate=False)

    async def _add_system_message(self, container: VerticalScroll, text: str) -> None:
        """Mount a system message into the message list."""
        msg_box = Vertical(classes="cmd-output")
        content = Markdown(text, classes="cmd-output-content")
        await container.mount(msg_box)
        await msg_box.mount(content)
        container.scroll_end(animate=False)

    @staticmethod
    def _is_near_bottom(container: VerticalScroll) -> bool:
        """Check if the user is scrolled near the bottom (within 5 lines)."""
        return container.scroll_y >= container.max_scroll_y - 5

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate: ~1 token per 4 characters."""
        return max(1, len(text) // 4)

    async def _refresh_workers(self) -> None:
        """Fetch workers from the backend and update the local cache."""
        if self._client is None:
            return
        try:
            self._worker_cache = await self._client.list_workers()
            self._known_roles = {w.role for w in self._worker_cache}
            self._role_descriptions = {
                w.role: w.description for w in self._worker_cache if w.description
            }
            # Build name-to-role alias mapping
            self._name_to_role = {}
            for w in self._worker_cache:
                if w.name:
                    lower_name = w.name.lower()
                    self._name_to_role[lower_name] = w.role
                    self._known_roles.add(lower_name)
        except Exception:
            # Keep fallback roles if the backend call fails.
            pass

    def _get_worker_display(self, role: str) -> tuple[str, str, str]:
        """Return (display_name, avatar, avatar_color) for a worker role."""
        for w in self._worker_cache:
            if w.role == role:
                return (w.name or role.replace("_", " ").title(), w.avatar, w.avatar_color)
        return (role.replace("_", " ").title(), "", "")

    def _extract_role(self, text: str) -> str | None:
        """Return the first known @role mention in the message text.

        Name mentions (e.g. ``@amara``) are resolved to the underlying role
        via ``_name_to_role``.  Direct role mentions (``@manager``) pass
        through unchanged.
        """
        for match in _MENTION_RE.finditer(text):
            mention = match.group(1).lower()
            if mention in self._known_roles:
                return self._name_to_role.get(mention, mention)
        return None

    def _hide_welcome(self) -> None:
        """Hide the welcome banner and show the message list."""
        welcome = self.query_one("#welcome", Vertical)
        if welcome.display:
            welcome.display = False
            self.query_one("#message-list", VerticalScroll).display = True

    def _update_input_hint(self, text: str = "") -> None:
        """Update the input hint to reflect the detected @role target."""
        if self._private_role:
            hint = f"Private chat with @{self._private_role} · Enter to send"
        elif not text:
            hint = "Enter to send · Shift+Enter for newline · /help for commands"
        else:
            # Capture the raw @mention text for display purposes.
            raw_mention: str | None = None
            raw_match = _MENTION_RE.search(text)
            if raw_match:
                raw_mention = raw_match.group(1).lower()

            role = self._extract_role(text)
            if role:
                # Look up the worker for rich display.
                worker_name, avatar, _ = self._get_worker_display(role)
                avatar_prefix = f"({avatar}) " if avatar else ""
                desc = self._role_descriptions.get(role, "")
                if raw_mention and raw_mention != role:
                    # Name-based mention: @amara -> (A) Amara · description
                    label = f"@{raw_mention} -> {avatar_prefix}{worker_name}"
                else:
                    # Role-based mention: @manager -> (A) Amara · description
                    label = f"@{role} -> {avatar_prefix}{worker_name}"
                if desc:
                    hint = f"{label} · {desc} · Enter to send"
                else:
                    hint = f"{label} · Enter to send"
            else:
                # Check for an unrecognised @mention to warn the user.
                if raw_mention and raw_mention not in self._known_roles:
                    hint = f"@{raw_mention} — unknown role · Enter to send"
                else:
                    hint = "Enter to send · Shift+Enter for newline · /help for commands"
        with contextlib.suppress(NoMatches):
            self.query_one("#input-hint", Static).update(hint)

    # ── File attachments ─────────────────────────────────────

    def _attach_file(self, path_str: str) -> str:
        """Read a file from *path_str* and add to pending attachments.

        Returns a status message string.
        """
        path = Path(path_str).expanduser().resolve()
        if not path.is_file():
            return f"**Error:** File not found: `{path}`"
        size = path.stat().st_size
        if size > MAX_ATTACHMENT_SIZE:
            limit_mb = MAX_ATTACHMENT_SIZE // (1024 * 1024)
            return f"**Error:** File too large ({size:,} bytes). Max {limit_mb}MB."
        if len(self._attachments) >= MAX_ATTACHMENTS:
            return f"**Error:** Maximum {MAX_ATTACHMENTS} attachments reached. Use `/detach` to clear."
        ext = path.suffix.lower()
        media_type = EXTENSION_MIME_MAP.get(ext, "application/octet-stream")
        data = path.read_bytes()
        att = FileAttachment(
            filename=path.name,
            media_type=media_type,
            data=data,
            size=len(data),
        )
        self._attachments.append(att)
        self._update_attachment_bar()
        return self._router.attach_text(path.name)

    def _clear_attachments(self) -> None:
        """Remove all pending attachments and update the UI."""
        self._attachments.clear()
        self._update_attachment_bar()

    def _update_attachment_bar(self) -> None:
        """Update (or hide) the attachment indicator above the input."""
        with contextlib.suppress(NoMatches):
            bar = self.query_one("#attachment-bar", Static)
            if self._attachments:
                parts = []
                for att in self._attachments:
                    size_kb = att.size / 1024
                    parts.append(f"{att.filename} ({size_kb:.0f}KB)")
                bar.update("Attachments: " + ", ".join(parts))
            else:
                bar.update("")

    # ── Slash commands ───────────────────────────────────────

    async def _handle_command(self, text: str) -> None:
        """Handle slash commands."""
        self._hide_welcome()
        message_list = self.query_one("#message-list", VerticalScroll)
        command, arg = self._router.parse(text)

        match command:
            case "/help":
                await self._add_system_message(message_list, self._router.help_text)

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
                    await self._add_system_message(
                        message_list,
                        "Usage: `/project <brief>`\n\n"
                        "Example: `/project Analyze Q4 sales data and create a report`",
                    )

            case "/conversations":
                await self._add_system_message(
                    message_list, self._router.conversations_text(),
                )

            case "/load":
                await self._cmd_load(message_list, arg)

            case "/new":
                self._conversation = None
                self._total_tokens = 0
                self.query_one("#token-count", Static).update("")
                message_list.remove_children()
                await self._add_system_message(
                    message_list,
                    "New conversation. Type a message to begin.",
                )

            case "/status":
                await self._add_system_message(
                    message_list,
                    self._router.status_text(self._conversation, self._total_tokens),
                )

            case "/config":
                await self._add_system_message(
                    message_list, self._router.config_text(),
                )

            case "/connectors":
                await self._cmd_connectors(message_list)

            case "/send":
                await self._cmd_send(message_list, arg)

            case "/channels":
                await self._cmd_channels(message_list, arg)

            case "/export":
                await self._add_system_message(
                    message_list,
                    self._router.export_text(self._conversation),
                )

            case "/autonomy":
                await self._add_system_message(
                    message_list,
                    self._router.autonomy_text(new_level=arg or None),
                )
                self._update_status_bar()

            case "/checkpoints":
                await self._add_system_message(
                    message_list,
                    self._router.checkpoints_text(),
                )

            case "/approve":
                await self._add_system_message(
                    message_list,
                    self._router.approve_text(arg),
                )

            case "/reject":
                await self._cmd_reject(message_list, arg)

            case "/setup":
                await self._cmd_setup()

            case "/quit":
                self.exit()

            case "/usage":
                if self._client is not None:
                    stats = await self._client.get_usage_stats()
                    lines = [
                        "**Usage Statistics:**\n",
                        f"- **Tokens:** {stats.total_tokens:,}",
                        f"- **Cost:** ${stats.total_cost_usd:.4f}",
                        f"- **Tasks completed:** {stats.tasks_completed}",
                        f"- **Avg response:** {stats.avg_response_ms:.0f}ms",
                    ]
                    if stats.by_model:
                        lines.append("\n**By model:**")
                        for model, count in stats.by_model.items():
                            lines.append(f"- `{model}`: {count}")
                    await self._add_system_message(message_list, "\n".join(lines))
                else:
                    await self._add_system_message(
                        message_list, self._router.usage_text()
                    )

            case "/delete":
                await self._add_system_message(
                    message_list, self._router.delete_text(arg)
                )

            case "/clear":
                message_list.remove_children()
                await self._add_system_message(
                    message_list,
                    "Chat cleared. Conversation history preserved — use `/delete` to remove.",
                )

            case "/retry":
                if self._conversation and self._conversation.messages:
                    last_user = None
                    for msg in reversed(self._conversation.messages):
                        if not msg.is_ai:
                            last_user = msg.content
                            break
                    if last_user:
                        await self._send_message(last_user)
                    else:
                        await self._add_system_message(
                            message_list, "**Error:** No previous user message to retry."
                        )
                else:
                    await self._add_system_message(
                        message_list, "**Error:** No conversation to retry."
                    )

            case "/models":
                await self._add_system_message(
                    message_list, self._router.models_text()
                )

            case "/model":
                text = self._router.model_text(arg)
                await self._add_system_message(message_list, text)
                if arg.strip():
                    self._update_model_label(arg.strip())

            case "/invite":
                result = self._router.invite_text(arg, known_roles=self._known_roles)
                await self._add_system_message(message_list, result)
                # Track invited role in conversation participants.
                role = arg.strip().lstrip("@").lower()
                if role in self._known_roles and self._conversation is not None:
                    if role not in self._conversation.participants:
                        self._conversation.participants.append(role)
                    self._update_participants_display()

            case "/private":
                role = arg.strip().lstrip("@").lower() if arg.strip() else None
                if role:
                    self._private_role = role
                else:
                    self._private_role = None
                await self._add_system_message(
                    message_list, self._router.private_text(role),
                )
                self._update_participants_display()
                self._update_input_hint()

            case "/attach":
                result = self._attach_file(arg)
                await self._add_system_message(message_list, result)

            case "/detach":
                self._clear_attachments()
                await self._add_system_message(
                    message_list, self._router.detach_text(),
                )

            case "/list":
                await self._cmd_list(message_list)

            case "/search":
                await self._cmd_search(message_list, arg)

            case "/rename":
                await self._cmd_rename(message_list, arg)

            case "/archive":
                await self._cmd_archive(message_list)

            case _:
                await self._add_system_message(
                    message_list,
                    f"Unknown command: `{command}`\n\nType `/help` for available commands.",
                )

    async def _cmd_team(self, container: VerticalScroll) -> None:
        """List available workers."""
        if self._client is None:
            await self._add_system_message(container, "Client not connected.")
            return
        workers = await self._client.list_workers()
        lines = ["**Your Team:**\n"]
        for w in workers:
            avatar = f"({w.avatar})" if w.avatar else ""
            name = w.name or w.role.replace("_", " ").title()
            tagline = w.tagline or w.description
            lines.append(f"{avatar} **{name}** \u00b7 @{w.role} \u00b7 {tagline}")
        await self._add_system_message(container, "\n".join(lines))

    async def _cmd_list_plans(self, container: VerticalScroll) -> None:
        """List available plans."""
        if self._client is None:
            await self._add_system_message(container, "Client not connected.")
            return
        plans = await self._client.list_plans()
        if plans:
            lines = ["**Available Plans:**\n"]
            for p in plans:
                roles = ", ".join(p.worker_roles) if p.worker_roles else "none"
                lines.append(f"- **{p.name}** ({p.steps} steps) — workers: {roles}")
            await self._add_system_message(container, "\n".join(lines))
        else:
            await self._add_system_message(container, "No plans available.")

    async def _cmd_execute_plan(self, container: VerticalScroll, plan_name: str) -> None:
        """Execute a named plan with streaming output."""
        if self._client is None:
            await self._add_system_message(container, "Client not connected.")
            return

        await self._add_system_message(container, f"Executing plan: **{plan_name}**...")

        content = Markdown("", classes="msg-content")
        box = Vertical(classes="msg-box-ai")
        header = Static("Planner", classes="msg-sender msg-sender-ai")
        await container.mount(box)
        await box.mount(header)
        await box.mount(content)

        indicator = ThinkingIndicator()
        await box.mount(indicator)
        container.scroll_end(animate=False)

        timer = ResponseTimer()
        timer.start()
        tokens: list[str] = []
        first_token_marked = False
        self._is_streaming = True
        try:
            try:
                async with asyncio.timeout(_STREAMING_TIMEOUT):
                    async for event in self._client.execute_plan(plan_name):
                        if self._cancel_streaming.is_set():
                            tokens.append("\n\n_[Cancelled by user]_")
                            await content.update("".join(tokens))
                            break
                        if event.type in ("token", "complete"):
                            if not first_token_marked:
                                first_token_marked = True
                                timer.mark_first_token()
                                indicator.set_streaming_mode(timer)
                            tokens.append(event.content)
                            await content.update("".join(tokens))
                            if self._is_near_bottom(container):
                                container.scroll_end(animate=False)
                        elif event.type == "error":
                            tokens.append(f"\n\n**Error:** {event.content}")
                            await content.update("".join(tokens))
            except TimeoutError:
                tokens.append("\n\n**Error:** Response timed out after 5 minutes.")
                await content.update("".join(tokens))
            except Exception as e:
                tokens.append(f"\n\n**Error:** {e}")
                await content.update("".join(tokens))
        finally:
            timer.stop()
            self._is_streaming = False
            self._cancel_streaming.clear()
            indicator.stop()
            indicator.remove()

        # Response summary
        final_content = "".join(tokens)
        token_estimate = self._estimate_tokens(final_content)
        self._total_tokens += token_estimate
        self.query_one("#token-count", Static).update(
            f" · ~{self._total_tokens:,} tokens"
        )
        summary = Static(timer.format_summary(token_estimate), classes="response-summary")
        await box.mount(summary)

    async def _cmd_load(self, container: VerticalScroll, conv_id: str) -> None:
        """Load a saved conversation by ID."""
        conv_id = conv_id.strip()
        if not conv_id:
            await self._add_system_message(
                container,
                "Usage: `/load <conversation-id>`\n\n"
                "Use `/conversations` to see available IDs.",
            )
            return

        conv = self._store.get_conversation(conv_id)
        if conv is None:
            await self._add_system_message(
                container, f"Conversation `{conv_id}` not found."
            )
            return

        self._conversation = conv
        container.remove_children()

        # Replay messages into the UI
        for msg in conv.messages:
            if msg.is_ai:
                msg_box = Vertical(classes="msg-box-ai")
                header = Static(
                    f"{msg.sender}",
                    classes="msg-sender msg-sender-ai",
                )
                content = Markdown(msg.content, classes="msg-content")
                await container.mount(msg_box)
                await msg_box.mount(header)
                await msg_box.mount(content)
            else:
                await self._add_user_message(container, msg.content)

        await self._add_system_message(
            container,
            f"Loaded conversation: **{conv.title}** ({len(conv.messages)} messages)",
        )

    async def _cmd_reject(self, container: VerticalScroll, arg: str) -> None:
        """Reject a checkpoint, with optional reason after the ID."""
        parts = arg.split(maxsplit=1)
        checkpoint_id = parts[0] if parts else ""
        reason = parts[1] if len(parts) > 1 else ""
        await self._add_system_message(
            container,
            self._router.reject_text(checkpoint_id, reason=reason),
        )

    async def _cmd_list(self, container) -> None:
        """List recent conversations."""
        convs = self._store.list_conversations()
        if not convs:
            await self._add_system_message(container, "No conversations yet.")
            return
        lines = ["**Recent Conversations**\n─────────────────────────────"]
        for c in convs[:20]:
            active = " *" if self._conversation and c.id == self._conversation.id else ""
            lines.append(
                f"  `{c.id[:12]}`  {c.title:<30}  {c.message_count} msgs{active}"
            )
        lines.append("─────────────────────────────")
        lines.append("`/load <id>` to resume · `/search <query>` to find")
        await self._add_system_message(container, "\n".join(lines))

    async def _cmd_search(self, container, query: str) -> None:
        """Search conversation messages."""
        if not query:
            await self._add_system_message(container, "Usage: `/search <query>`")
            return
        results = self._store.search(query)
        if not results:
            await self._add_system_message(container, f'No results for "{query}".')
            return
        lines = [f'**Search results for "{query}"**\n─────────────────────────────']
        for r in results[:10]:
            snippet = r["content"][:120]
            lines.append(f"  `{r['conversation_id'][:12]}`  [{r['sender']}] {snippet}")
        lines.append("─────────────────────────────")
        await self._add_system_message(container, "\n".join(lines))

    async def _cmd_rename(self, container, title: str) -> None:
        """Rename the current conversation."""
        if not self._conversation:
            await self._add_system_message(container, "No active conversation.")
            return
        if not title:
            await self._add_system_message(container, "Usage: `/rename <new title>`")
            return
        self._conversation.title = title
        self._store._save_conversation(self._conversation)
        self._store._update_index(self._conversation)
        self._store._upsert_conversation_row(self._conversation)
        await self._add_system_message(container, f'Conversation renamed to "{title}".')

    async def _cmd_archive(self, container) -> None:
        """Archive the current conversation."""
        if not self._conversation:
            await self._add_system_message(container, "No active conversation.")
            return
        self._conversation.status = "archived"
        self._store._save_conversation(self._conversation)
        self._store._update_index(self._conversation)
        self._store._upsert_conversation_row(self._conversation)
        title = self._conversation.title
        self._conversation = None
        await self._add_system_message(container, f'Conversation "{title}" archived.')

    async def _cmd_connectors(self, container: VerticalScroll) -> None:
        """List all connector statuses."""
        if self._client is None:
            await self._add_system_message(container, "Client not connected.")
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
            await self._add_system_message(container, "\n".join(lines))
        else:
            await self._add_system_message(container, "No connectors available.")

    async def _cmd_setup(self) -> None:
        """Re-run the setup wizard."""
        from firefly_dworkers_cli.tui.screens.setup import SetupWizard

        await self.push_screen(
            SetupWizard(self._config_mgr),
            callback=self._on_setup_complete,
        )

    # ── Project commands ──────────────────────────────────────

    async def _cmd_project(self, container: VerticalScroll, brief: str) -> None:
        """Run a multi-worker project from a brief."""
        if self._client is None:
            await self._add_system_message(container, "Client not connected.")
            return

        await self._add_system_message(
            container,
            f"Starting project: **{brief[:60]}{'...' if len(brief) > 60 else ''}**",
        )

        content_widget = Markdown("", classes="msg-content")
        msg_box = Vertical(classes="msg-box-ai")
        header = Static(
            "Project Orchestrator",
            classes="msg-sender msg-sender-ai",
        )
        await container.mount(msg_box)
        await msg_box.mount(header)
        await msg_box.mount(content_widget)

        indicator = ThinkingIndicator()
        await msg_box.mount(indicator)
        container.scroll_end(animate=False)

        timer = ResponseTimer()
        timer.start()
        tokens: list[str] = []
        first_token_marked = False
        self._is_streaming = True
        try:
            try:
                async with asyncio.timeout(_STREAMING_TIMEOUT):
                    async for event in self._client.run_project(brief):
                        if self._cancel_streaming.is_set():
                            tokens.append("\n\n_[Cancelled by user]_")
                            await content_widget.update("".join(tokens))
                            break
                        if event.type in ("project_start", "project_complete"):
                            if not first_token_marked:
                                first_token_marked = True
                                timer.mark_first_token()
                                indicator.set_streaming_mode(timer)
                            tokens.append(f"\n**{event.type}:** {event.content}\n")
                        elif event.type == "task_assigned":
                            tokens.append(f"\n> Task assigned: {event.content}\n")
                        elif event.type == "task_complete":
                            tokens.append(f"\n> Task complete: {event.content}\n")
                        elif event.type in ("token", "complete"):
                            if not first_token_marked:
                                first_token_marked = True
                                timer.mark_first_token()
                                indicator.set_streaming_mode(timer)
                            tokens.append(event.content)
                        elif event.type == "error":
                            tokens.append(f"\n\n**Error:** {event.content}")
                        else:
                            tokens.append(f"\n{event.content}")
                        await content_widget.update("".join(tokens))
                        if self._is_near_bottom(container):
                            container.scroll_end(animate=False)
            except TimeoutError:
                tokens.append("\n\n**Error:** Response timed out after 5 minutes.")
                await content_widget.update("".join(tokens))
            except Exception as e:
                tokens.append(f"\n\n**Error:** {e}")
                await content_widget.update("".join(tokens))
        finally:
            timer.stop()
            self._is_streaming = False
            self._cancel_streaming.clear()
            indicator.stop()
            indicator.remove()

        # Response summary
        final_content = "".join(tokens)
        token_estimate = self._estimate_tokens(final_content)
        self._total_tokens += token_estimate
        self.query_one("#token-count", Static).update(
            f" · ~{self._total_tokens:,} tokens"
        )
        summary = Static(timer.format_summary(token_estimate), classes="response-summary")
        await msg_box.mount(summary)

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
            await self._add_system_message(
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
            await self._add_system_message(
                container,
                f"Messaging tool `{tool_name}` is not configured.\n\n"
                "Available: slack, teams, email.\n"
                "Configure via `~/.dworkers/config.yaml` or run `/setup`.",
            )
            return

        await self._add_system_message(
            container, f"Sending via **{tool_name}** to `{channel}`..."
        )
        try:
            result = await tool.execute(
                action="send", channel=channel, content=message
            )
            msg_id = result.get("id", "unknown")
            await self._add_system_message(
                container,
                f"Message sent successfully (id: `{msg_id}`)",
            )
        except Exception as e:
            await self._add_system_message(
                container, f"**Error sending message:** {e}"
            )

    async def _cmd_channels(self, container: VerticalScroll, arg: str) -> None:
        """List channels for a messaging tool.

        Usage: /channels <tool>
        Example: /channels slack
        """
        tool_name = arg.strip()
        if not tool_name:
            await self._add_system_message(
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
            await self._add_system_message(
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
                await self._add_system_message(container, "\n".join(lines))
            else:
                await self._add_system_message(
                    container, f"No channels found for {tool_name}."
                )
        except Exception as e:
            await self._add_system_message(
                container, f"**Error listing channels:** {e}"
            )

    # ── Actions ──────────────────────────────────────────────

    async def action_new_conversation(self) -> None:
        """Start a new conversation."""
        self._conversation = None
        self._total_tokens = 0
        self.query_one("#token-count", Static).update("")
        message_list = self.query_one("#message-list", VerticalScroll)
        message_list.remove_children()
        await self._add_system_message(
            message_list,
            "New conversation. Type a message to begin.",
        )

    def action_cancel_or_quit(self) -> None:
        """Ctrl+C: cancel streaming, or double-press within 2s to quit."""
        if self._is_streaming:
            self._cancel_streaming.set()
            with contextlib.suppress(Exception):
                for ind in self.query(".streaming-indicator"):
                    ind.update("Cancelling...")
            return
        now = time.monotonic()
        if now - self._last_ctrl_c < 2.0:
            self.exit()
        else:
            self._last_ctrl_c = now
            with contextlib.suppress(NoMatches):
                self.query_one("#input-hint", Static).update(
                    "Press Ctrl+C again to quit"
                )
            # Reset hint after 2 seconds
            self.set_timer(2.0, self._reset_quit_hint)

    async def action_clear_chat(self) -> None:
        """Clear the chat display (Ctrl+L)."""
        message_list = self.query_one("#message-list", VerticalScroll)
        message_list.remove_children()
        await self._add_system_message(
            message_list,
            "Chat cleared. Conversation history preserved — use `/delete` to remove.",
        )

    def _reset_quit_hint(self) -> None:
        """Reset the input hint after the Ctrl+C quit window expires."""
        self._update_input_hint()

    def action_focus_input(self) -> None:
        """Focus the input area."""
        self.query_one("#prompt-input", PromptInput).focus()
