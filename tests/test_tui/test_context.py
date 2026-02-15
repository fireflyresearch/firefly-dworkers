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
