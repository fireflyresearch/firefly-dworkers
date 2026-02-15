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
