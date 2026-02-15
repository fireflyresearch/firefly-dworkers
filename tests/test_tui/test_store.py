"""Tests for ConversationStore with SQLite index."""
from __future__ import annotations
from pathlib import Path
import pytest
from firefly_dworkers_cli.tui.backend.models import ChatMessage
from firefly_dworkers_cli.tui.backend.store import ConversationStore


class TestSQLiteIndex:
    def test_store_creates_db(self, tmp_path: Path):
        store = ConversationStore(base_dir=tmp_path / "convs")
        db_path = tmp_path / "convs" / "state.db"
        assert db_path.exists()

    def test_create_conversation_indexed(self, tmp_path: Path):
        store = ConversationStore(base_dir=tmp_path / "convs")
        conv = store.create_conversation("Test chat")
        convs = store.list_conversations()
        assert len(convs) == 1
        assert convs[0].id == conv.id
        assert convs[0].title == "Test chat"

    def test_add_message_updates_index(self, tmp_path: Path):
        from datetime import datetime, timezone
        store = ConversationStore(base_dir=tmp_path / "convs")
        conv = store.create_conversation("Test")
        msg = ChatMessage(
            id="msg_1", conversation_id=conv.id, role="user", sender="You",
            content="Hello world", timestamp=datetime.now(timezone.utc),
        )
        store.add_message(conv.id, msg)
        summaries = store.list_conversations()
        assert summaries[0].message_count == 1

    def test_search_messages(self, tmp_path: Path):
        from datetime import datetime, timezone
        store = ConversationStore(base_dir=tmp_path / "convs")
        conv = store.create_conversation("Market Analysis")
        msg = ChatMessage(
            id="msg_1", conversation_id=conv.id, role="analyst", sender="Leo",
            content="The competitor analysis shows strong growth in enterprise.",
            timestamp=datetime.now(timezone.utc), is_ai=True,
        )
        store.add_message(conv.id, msg)
        results = store.search("competitor")
        assert len(results) >= 1
        assert "competitor" in results[0]["content"].lower()

    def test_delete_removes_from_index(self, tmp_path: Path):
        store = ConversationStore(base_dir=tmp_path / "convs")
        conv = store.create_conversation("To delete")
        store.delete_conversation(conv.id)
        assert len(store.list_conversations()) == 0


class TestSessionState:
    def test_save_and_load_session_state(self, tmp_path: Path):
        store = ConversationStore(base_dir=tmp_path / "convs")
        store.save_session_state({"active_conversation_id": "conv_abc123", "total_tokens": "5000"})
        state = store.load_session_state()
        assert state["active_conversation_id"] == "conv_abc123"
        assert state["total_tokens"] == "5000"

    def test_session_state_defaults_empty(self, tmp_path: Path):
        store = ConversationStore(base_dir=tmp_path / "convs")
        state = store.load_session_state()
        assert state == {}
