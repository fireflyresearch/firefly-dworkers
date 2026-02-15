"""Tests for conversation context building and token counting."""
from __future__ import annotations


class TestTokenCounter:
    def test_count_returns_positive_int(self):
        from firefly_dworkers_cli.tui.backend.context import TokenCounter
        counter = TokenCounter()
        count = counter.count("Hello, this is a test message.")
        assert isinstance(count, int)
        assert count > 0

    def test_count_empty_string(self):
        from firefly_dworkers_cli.tui.backend.context import TokenCounter
        counter = TokenCounter()
        assert counter.count("") == 0

    def test_count_scales_with_length(self):
        from firefly_dworkers_cli.tui.backend.context import TokenCounter
        counter = TokenCounter()
        short = counter.count("Hello")
        long = counter.count("Hello " * 100)
        assert long > short

    def test_count_message(self):
        from datetime import datetime, timezone
        from firefly_dworkers_cli.tui.backend.context import TokenCounter
        from firefly_dworkers_cli.tui.backend.models import ChatMessage
        counter = TokenCounter()
        msg = ChatMessage(
            id="m1", conversation_id="c1", role="user", sender="You",
            content="Hello world", timestamp=datetime.now(timezone.utc),
        )
        count = counter.count_message(msg)
        assert count > 0

    def test_model_context_limit(self):
        from firefly_dworkers_cli.tui.backend.context import TokenCounter
        assert TokenCounter.get_model_context_limit("gpt-4") >= 128000
        assert TokenCounter.get_model_context_limit("claude-3") >= 200000
        assert TokenCounter.get_model_context_limit("unknown") >= 100000


from datetime import datetime, timezone

from firefly_dworkers_cli.tui.backend.models import ChatMessage


def _make_message(content: str, sender: str = "You", role: str = "user", is_ai: bool = False) -> ChatMessage:
    return ChatMessage(
        id=f"msg_{hash(content) % 10000}",
        conversation_id="conv_test",
        role=role,
        sender=sender,
        content=content,
        timestamp=datetime.now(timezone.utc),
        is_ai=is_ai,
    )


class TestConversationContextBuilder:
    def test_small_conversation_returns_all(self):
        from firefly_dworkers_cli.tui.backend.context import ConversationContextBuilder
        builder = ConversationContextBuilder()
        messages = [_make_message(f"Message {i}") for i in range(5)]
        context = builder.build(messages)
        assert "Message 0" in context
        assert "Message 4" in context

    def test_large_conversation_splits_recent(self):
        from firefly_dworkers_cli.tui.backend.context import ConversationContextBuilder, CONTEXT_RECENT_COUNT
        builder = ConversationContextBuilder()
        messages = [_make_message(f"Message {i}") for i in range(30)]
        context = builder.build(messages)
        # Recent messages should be verbatim
        assert "Message 29" in context
        assert "Message 28" in context
        # Should have a summary section header
        assert "CONVERSATION SUMMARY" in context or "RECENT MESSAGES" in context

    def test_format_messages_includes_sender(self):
        from firefly_dworkers_cli.tui.backend.context import ConversationContextBuilder
        builder = ConversationContextBuilder()
        messages = [
            _make_message("Hello", sender="You", role="user"),
            _make_message("Hi there!", sender="Amara", role="manager", is_ai=True),
        ]
        context = builder.build(messages)
        assert "[You]" in context
        assert "[Amara]" in context


class TestProjectContextInBuilder:
    def test_build_with_project_context(self):
        from firefly_dworkers_cli.tui.backend.context import ConversationContextBuilder
        builder = ConversationContextBuilder()
        messages = [_make_message(f"Message {i}") for i in range(3)]
        context = builder.build(
            messages,
            project_context="Project: EV Analysis\nFact: market_size = $4.2B",
        )
        assert "PROJECT CONTEXT" in context
        assert "market_size" in context
        assert "Message 0" in context

    def test_build_without_project_context(self):
        from firefly_dworkers_cli.tui.backend.context import ConversationContextBuilder
        builder = ConversationContextBuilder()
        messages = [_make_message("Hello")]
        context = builder.build(messages)
        assert "PROJECT CONTEXT" not in context


class TestCompactionEngine:
    def test_should_compact_under_threshold(self):
        from firefly_dworkers_cli.tui.backend.context import CompactionEngine
        engine = CompactionEngine()
        assert engine.should_compact(token_count=5000, model_limit=128000) is False

    def test_should_compact_over_threshold(self):
        from firefly_dworkers_cli.tui.backend.context import CompactionEngine
        engine = CompactionEngine()
        assert engine.should_compact(token_count=90000, model_limit=128000) is True

    def test_compact_returns_reduced_context(self):
        from firefly_dworkers_cli.tui.backend.context import CompactionEngine, CONTEXT_RECENT_COUNT
        engine = CompactionEngine()
        messages = [_make_message(f"Message {i}", sender="You" if i % 2 == 0 else "Amara") for i in range(30)]
        result = engine.compact(messages)
        assert result.summary != ""
        assert len(result.recent_messages) == CONTEXT_RECENT_COUNT
        assert result.compacted_count == 30 - CONTEXT_RECENT_COUNT

    def test_compact_small_conversation_noop(self):
        from firefly_dworkers_cli.tui.backend.context import CompactionEngine
        engine = CompactionEngine()
        messages = [_make_message(f"Message {i}") for i in range(5)]
        result = engine.compact(messages)
        assert result.compacted_count == 0
        assert len(result.recent_messages) == 5
