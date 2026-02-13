"""Test TUI widgets."""

from datetime import UTC, datetime

from firefly_dworkers_cli.tui.widgets.message_bubble import MessageBubble
from firefly_dworkers_cli.tui.widgets.status_badge import StatusBadge
from firefly_dworkers_cli.tui.widgets.streaming_bubble import StreamingBubble


class TestMessageBubble:
    def test_user_message(self):
        msg = MessageBubble(
            sender="Alice",
            content="Hello",
            timestamp=datetime.now(UTC),
            is_ai=False,
        )
        assert "message-bubble-user" in msg.classes

    def test_ai_message(self):
        msg = MessageBubble(
            sender="Researcher",
            content="Analysis complete",
            timestamp=datetime.now(UTC),
            is_ai=True,
            role="researcher",
        )
        assert "message-bubble-agent" in msg.classes


class TestStreamingBubble:
    def test_append_tokens(self):
        bubble = StreamingBubble(sender="Analyst", role="analyst")
        bubble.append_token("Hello ")
        bubble.append_token("world")
        assert bubble.full_content == "Hello world"

    def test_finalize(self):
        bubble = StreamingBubble(sender="Analyst")
        bubble.append_token("Done")
        final = bubble.finalize()
        assert isinstance(final, MessageBubble)


class TestStatusBadge:
    def test_success_variant(self):
        badge = StatusBadge("OK", variant="success")
        assert "badge" in badge.classes
