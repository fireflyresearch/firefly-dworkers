"""Conversation persistence to ~/.dworkers/conversations/."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from firefly_dworkers_cli.tui.backend.models import (
    ChatMessage,
    Conversation,
    ConversationSummary,
)


class ConversationStore:
    """File-backed conversation storage."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or Path.home() / ".dworkers" / "conversations"
        self._base.mkdir(parents=True, exist_ok=True)
        self._index_path = self._base / "index.json"

    def list_conversations(self) -> list[ConversationSummary]:
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
        return conv

    def add_message(self, conv_id: str, message: ChatMessage) -> None:
        conv = self.get_conversation(conv_id)
        if conv is None:
            raise ValueError(f"Conversation {conv_id} not found")
        conv.messages.append(message)
        conv.updated_at = datetime.now(UTC)
        self._save_conversation(conv)
        self._update_index(conv)

    def delete_conversation(self, conv_id: str) -> None:
        path = self._base / f"{conv_id}.json"
        path.unlink(missing_ok=True)
        summaries = [s for s in self.list_conversations() if s.id != conv_id]
        self._write_index(summaries)

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
