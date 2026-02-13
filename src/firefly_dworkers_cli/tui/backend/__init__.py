"""Backend bridge -- local and remote clients."""

from firefly_dworkers_cli.tui.backend.client import (
    DworkersClient,
    create_client,
)
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

__all__ = [
    "ChatMessage",
    "ConnectorStatus",
    "Conversation",
    "ConversationStore",
    "ConversationSummary",
    "DworkersClient",
    "PlanInfo",
    "UsageStats",
    "WorkerInfo",
    "create_client",
]
