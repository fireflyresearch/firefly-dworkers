"""Conversations API router -- conversations are client-side only.

Conversations are stored locally in ``~/.dworkers/conversations/`` and managed
by the TUI's :class:`ConversationStore`.  In remote mode the server does not
manage conversation state, so this endpoint returns an empty list.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ConversationResponse(BaseModel):
    """Placeholder response -- conversations are client-side only."""

    pass


@router.get("")
async def list_conversations(tenant_id: str = "default") -> list[ConversationResponse]:
    """List conversations.

    Returns an empty list because conversations are managed client-side
    in the TUI's local storage (``~/.dworkers/conversations/``).
    """
    return []
