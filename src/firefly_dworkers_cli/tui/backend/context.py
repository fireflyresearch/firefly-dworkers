"""Conversation context building, summarization, and token counting."""
from __future__ import annotations

from firefly_dworkers_cli.tui.backend.models import ChatMessage

CONTEXT_RECENT_COUNT = 15
SUMMARY_TRIGGER = 20
RESUMMARIZE_THRESHOLD = 20
AUTO_COMPACT_RATIO = 0.7

_MODEL_CONTEXT_LIMITS: dict[str, int] = {
    "gpt-4": 128_000,
    "gpt-5": 128_000,
    "claude": 200_000,
    "gemini": 128_000,
    "mistral": 32_000,
    "llama": 8_000,
}
DEFAULT_CONTEXT_LIMIT = 128_000


class TokenCounter:
    """Approximate token counting for context management."""

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def count_message(self, message: ChatMessage) -> int:
        overhead = 4
        return self.count(message.content) + overhead

    def count_messages(self, messages: list[ChatMessage]) -> int:
        return sum(self.count_message(m) for m in messages)

    @staticmethod
    def get_model_context_limit(model: str = "") -> int:
        model_lower = model.lower()
        for prefix, limit in _MODEL_CONTEXT_LIMITS.items():
            if prefix in model_lower:
                return limit
        return DEFAULT_CONTEXT_LIMIT


class ConversationContextBuilder:
    """Builds conversation context with hierarchical summary + recent messages."""

    def __init__(self) -> None:
        self._counter = TokenCounter()

    def build(self, messages: list[ChatMessage], *, cached_summary: str = "") -> str:
        if not messages:
            return ""

        total = len(messages)

        if total <= CONTEXT_RECENT_COUNT:
            return self._format_messages(messages)

        older = messages[:-CONTEXT_RECENT_COUNT]
        recent = messages[-CONTEXT_RECENT_COUNT:]

        summary = cached_summary or self._simple_summary(older)

        return (
            f"--- CONVERSATION SUMMARY (older messages) ---\n{summary}\n\n"
            f"--- RECENT MESSAGES ---\n{self._format_messages(recent)}"
        )

    def _format_messages(self, messages: list[ChatMessage]) -> str:
        lines = []
        for msg in messages:
            lines.append(f"[{msg.sender}] {msg.content}")
        return "\n".join(lines)

    def _simple_summary(self, messages: list[ChatMessage]) -> str:
        if not messages:
            return ""
        participants = {m.sender for m in messages}
        first_content = messages[0].content[:100]
        last_content = messages[-1].content[:100]
        return (
            f"Conversation with {', '.join(sorted(participants))} "
            f"({len(messages)} messages). "
            f"Started with: \"{first_content}...\" "
            f"Last topic: \"{last_content}...\""
        )

    def needs_summary(self, message_count: int, cached_summary_count: int = 0) -> bool:
        uncovered = message_count - cached_summary_count
        return uncovered >= SUMMARY_TRIGGER
