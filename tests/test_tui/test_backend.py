"""Test backend models, store, and client factory."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from firefly_dworkers_cli.tui.backend.models import (
    ChatMessage,
    ConnectorStatus,
    Conversation,
    ConversationSummary,
    PlanInfo,
    UsageStats,
    WorkerInfo,
)
from firefly_dworkers_cli.tui.backend.store import ConversationStore

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestBackendModels:
    def test_worker_info_defaults(self) -> None:
        w = WorkerInfo(role="analyst", name="Analyst")
        assert w.role == "analyst"
        assert w.enabled is True
        assert w.autonomy == "semi_supervised"
        assert w.tools == []

    def test_chat_message(self) -> None:
        msg = ChatMessage(
            id="m1",
            conversation_id="c1",
            role="user",
            sender="Alice",
            content="Hello",
            timestamp=datetime.now(UTC),
        )
        assert msg.is_ai is False
        assert msg.status == "complete"

    def test_conversation_summary(self) -> None:
        s = ConversationSummary(
            id="c1",
            title="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert s.message_count == 0
        assert s.status == "active"

    def test_conversation(self) -> None:
        c = Conversation(
            id="c1",
            title="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert c.tenant_id == "default"
        assert c.messages == []

    def test_plan_info(self) -> None:
        p = PlanInfo(name="market_analysis")
        assert p.steps == 0
        assert p.worker_roles == []

    def test_connector_status(self) -> None:
        c = ConnectorStatus(name="slack", category="messaging", configured=True)
        assert c.configured is True
        assert c.error == ""

    def test_usage_stats_defaults(self) -> None:
        u = UsageStats()
        assert u.total_tokens == 0
        assert u.total_cost_usd == 0.0
        assert u.by_model == {}


# ---------------------------------------------------------------------------
# ConversationStore tests
# ---------------------------------------------------------------------------


class TestConversationStore:
    def test_create_and_list(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        conv = store.create_conversation("Test Chat")
        assert conv.title == "Test Chat"
        assert conv.id.startswith("conv_")

        convs = store.list_conversations()
        assert len(convs) == 1
        assert convs[0].id == conv.id

    def test_get_conversation(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        conv = store.create_conversation("Test")
        loaded = store.get_conversation(conv.id)
        assert loaded is not None
        assert loaded.title == "Test"
        assert loaded.id == conv.id

    def test_get_nonexistent_returns_none(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        assert store.get_conversation("conv_does_not_exist") is None

    def test_add_message(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        conv = store.create_conversation("Test")
        msg = ChatMessage(
            id="m1",
            conversation_id=conv.id,
            role="user",
            sender="Alice",
            content="Hello",
            timestamp=datetime.now(UTC),
        )
        store.add_message(conv.id, msg)

        loaded = store.get_conversation(conv.id)
        assert loaded is not None
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "Hello"

        # Index should reflect the message count
        summaries = store.list_conversations()
        assert summaries[0].message_count == 1

    def test_add_message_to_missing_conversation(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        msg = ChatMessage(
            id="m1",
            conversation_id="missing",
            role="user",
            sender="Alice",
            content="Hello",
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(ValueError, match="not found"):
            store.add_message("missing", msg)

    def test_delete_conversation(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        conv = store.create_conversation("To Delete")
        store.delete_conversation(conv.id)
        assert store.get_conversation(conv.id) is None
        assert len(store.list_conversations()) == 0

    def test_multiple_conversations_ordering(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        conv1 = store.create_conversation("First")
        conv2 = store.create_conversation("Second")

        summaries = store.list_conversations()
        assert len(summaries) == 2
        # Most recently created/updated should be first
        assert summaries[0].id == conv2.id
        assert summaries[1].id == conv1.id

    def test_empty_store_returns_empty_list(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        assert store.list_conversations() == []

    def test_create_with_tags(self, tmp_path: Path) -> None:
        store = ConversationStore(base_dir=tmp_path)
        conv = store.create_conversation(
            "Tagged Chat", tags=["important", "project-x"]
        )
        assert conv.tags == ["important", "project-x"]

        loaded = store.get_conversation(conv.id)
        assert loaded is not None
        assert loaded.tags == ["important", "project-x"]
