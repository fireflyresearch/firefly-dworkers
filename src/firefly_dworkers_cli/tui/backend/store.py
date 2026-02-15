"""Conversation persistence to ~/.dworkers/conversations/.

JSON files remain the source of truth for conversation data.
A SQLite database (state.db) provides fast indexing, FTS search,
and session-state storage alongside the JSON files.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

from firefly_dworkers_cli.tui.backend.models import (
    ChatMessage,
    Conversation,
    ConversationSummary,
)


class ConversationStore:
    """File-backed conversation storage with SQLite index."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or Path.home() / ".dworkers" / "conversations"
        self._base.mkdir(parents=True, exist_ok=True)
        self._index_path = self._base / "index.json"
        self._db_path = self._base / "state.db"
        self._init_db()

    # ── SQLite infrastructure ──────────────────────────────────────

    def _init_db(self) -> None:
        """Create SQLite tables if they don't already exist."""
        with self._db() as conn:
            conn.executescript(
                """\
                CREATE TABLE IF NOT EXISTS conversations (
                    id            TEXT PRIMARY KEY,
                    title         TEXT NOT NULL,
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL,
                    participants  TEXT NOT NULL DEFAULT '[]',
                    message_count INTEGER NOT NULL DEFAULT 0,
                    status        TEXT NOT NULL DEFAULT 'active',
                    tags          TEXT NOT NULL DEFAULT '[]'
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    message_id,
                    conversation_id,
                    role,
                    sender,
                    content,
                    timestamp
                );

                CREATE TABLE IF NOT EXISTS session_state (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS compactions (
                    id              TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    created_at      TEXT NOT NULL,
                    token_count     INTEGER NOT NULL DEFAULT 0,
                    summary         TEXT NOT NULL DEFAULT ''
                );
                """
            )

    @contextmanager
    def _db(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a SQLite connection with row-factory and auto-commit."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ── Public API ─────────────────────────────────────────────────

    def list_conversations(self) -> list[ConversationSummary]:
        """Return conversation summaries from SQLite index.

        Falls back to index.json when the SQLite table is empty
        (backward compatibility for stores created before the migration).
        """
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC"
            ).fetchall()

        if rows:
            return [
                ConversationSummary(
                    id=r["id"],
                    title=r["title"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    participants=json.loads(r["participants"]),
                    message_count=r["message_count"],
                    status=r["status"],
                    tags=json.loads(r["tags"]),
                )
                for r in rows
            ]

        # Fallback: read legacy index.json
        if not self._index_path.exists():
            return []
        data = json.loads(self._index_path.read_text())
        return [ConversationSummary.model_validate(c) for c in data]

    def get_conversation(self, conv_id: str) -> Conversation | None:
        path = self._base / f"{conv_id}.json"
        if not path.exists():
            return None
        return Conversation.model_validate_json(path.read_text())

    def create_conversation(
        self,
        title: str,
        *,
        tenant_id: str = "default",
        tags: list[str] | None = None,
    ) -> Conversation:
        conv = Conversation(
            id=f"conv_{uuid.uuid4().hex[:12]}",
            title=title,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            tenant_id=tenant_id,
            tags=tags or [],
        )
        self._save_conversation(conv)
        self._update_index(conv)
        self._upsert_conversation_row(conv)
        return conv

    def add_message(self, conv_id: str, message: ChatMessage) -> None:
        conv = self.get_conversation(conv_id)
        if conv is None:
            raise ValueError(f"Conversation {conv_id} not found")
        conv.messages.append(message)
        conv.updated_at = datetime.now(UTC)
        self._save_conversation(conv)
        self._update_index(conv)
        self._upsert_conversation_row(conv)
        self._index_message(message)

    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation by ID. Returns True if found and deleted."""
        path = self._base / f"{conv_id}.json"
        if path.exists():
            path.unlink()
            summaries = [s for s in self.list_conversations() if s.id != conv_id]
            self._write_index(summaries)
            self._delete_conversation_row(conv_id)
            return True
        return False

    def search(self, query: str) -> list[dict[str, Any]]:
        """Full-text search across message content via FTS5.

        Returns a list of dicts with keys: message_id, conversation_id,
        role, sender, content, timestamp.
        """
        with self._db() as conn:
            rows = conn.execute(
                "SELECT * FROM messages_fts WHERE messages_fts MATCH ? ORDER BY rank",
                (query,),
            ).fetchall()
        return [dict(r) for r in rows]

    def save_session_state(self, state: dict[str, str]) -> None:
        """Persist key/value session state into SQLite."""
        with self._db() as conn:
            for key, value in state.items():
                conn.execute(
                    "INSERT OR REPLACE INTO session_state (key, value) VALUES (?, ?)",
                    (key, value),
                )

    def load_session_state(self) -> dict[str, str]:
        """Load all session state key/value pairs from SQLite."""
        with self._db() as conn:
            rows = conn.execute("SELECT key, value FROM session_state").fetchall()
        return {r["key"]: r["value"] for r in rows}

    # ── Private helpers ────────────────────────────────────────────

    def _save_conversation(self, conv: Conversation) -> None:
        path = self._base / f"{conv.id}.json"
        path.write_text(conv.model_dump_json(indent=2))

    def _update_index(self, conv: Conversation) -> None:
        summaries = self.list_conversations()
        summaries = [s for s in summaries if s.id != conv.id]
        summaries.insert(
            0,
            ConversationSummary(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                participants=conv.participants,
                message_count=len(conv.messages),
                status=conv.status,
                tags=conv.tags,
            ),
        )
        self._write_index(summaries)

    def _write_index(self, summaries: list[ConversationSummary]) -> None:
        data = [s.model_dump(mode="json") for s in summaries]
        self._index_path.write_text(json.dumps(data, indent=2, default=str))

    def _upsert_conversation_row(self, conv: Conversation) -> None:
        """Insert or update the SQLite conversations table."""
        with self._db() as conn:
            conn.execute(
                """\
                INSERT INTO conversations
                    (id, title, created_at, updated_at, participants,
                     message_count, status, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title         = excluded.title,
                    updated_at    = excluded.updated_at,
                    participants  = excluded.participants,
                    message_count = excluded.message_count,
                    status        = excluded.status,
                    tags          = excluded.tags
                """,
                (
                    conv.id,
                    conv.title,
                    conv.created_at.isoformat(),
                    conv.updated_at.isoformat(),
                    json.dumps(conv.participants),
                    len(conv.messages),
                    conv.status,
                    json.dumps(conv.tags),
                ),
            )

    def _index_message(self, message: ChatMessage) -> None:
        """Insert a message into the FTS5 index."""
        with self._db() as conn:
            conn.execute(
                """\
                INSERT INTO messages_fts
                    (message_id, conversation_id, role, sender, content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.conversation_id,
                    message.role,
                    message.sender,
                    message.content,
                    message.timestamp.isoformat(),
                ),
            )

    def _delete_conversation_row(self, conv_id: str) -> None:
        """Remove a conversation and its messages from the SQLite index."""
        with self._db() as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.execute(
                "DELETE FROM messages_fts WHERE conversation_id = ?", (conv_id,)
            )
