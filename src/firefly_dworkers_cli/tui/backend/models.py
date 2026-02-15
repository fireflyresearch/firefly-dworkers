"""Data models for the TUI backend bridge."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkerInfo(BaseModel):
    role: str
    name: str
    description: str = ""
    tagline: str = ""
    avatar: str = ""
    avatar_color: str = ""
    enabled: bool = True
    autonomy: str = "semi_supervised"
    model: str = ""
    tools: list[str] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    participants: list[str] = Field(default_factory=list)
    message_count: int = 0
    status: str = "active"
    tags: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    id: str
    conversation_id: str
    role: str  # "user" or worker role name
    sender: str  # display name
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_ai: bool = False
    status: str = "complete"  # "complete", "streaming", "error"


class Conversation(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    participants: list[str] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)
    status: str = "active"
    tags: list[str] = Field(default_factory=list)
    tenant_id: str = "default"


class PlanInfo(BaseModel):
    name: str
    description: str = ""
    steps: int = 0
    worker_roles: list[str] = Field(default_factory=list)


class ConnectorStatus(BaseModel):
    name: str
    category: str  # "storage", "messaging", "project_management", etc.
    configured: bool = False
    provider: str = ""
    error: str = ""


class UsageStats(BaseModel):
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    tasks_completed: int = 0
    conversations: int = 0
    avg_response_ms: float = 0.0
    by_model: dict[str, int] = Field(default_factory=dict)
    by_worker: dict[str, int] = Field(default_factory=dict)


# Maximum file size (10 MB) and maximum number of attachments.
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
MAX_ATTACHMENTS = 5

# MIME types for supported file categories.
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_DOCUMENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/x-yaml",
    "text/xml",
}

# Extension → MIME type mapping for common file types.
EXTENSION_MIME_MAP: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".xml": "text/xml",
    # Code files — treated as plain text.
    ".py": "text/plain",
    ".js": "text/plain",
    ".ts": "text/plain",
    ".go": "text/plain",
    ".rs": "text/plain",
    ".java": "text/plain",
    ".c": "text/plain",
    ".cpp": "text/plain",
    ".h": "text/plain",
    ".rb": "text/plain",
    ".sh": "text/plain",
    ".sql": "text/plain",
    ".html": "text/html",
    ".css": "text/css",
}


class FileAttachment(BaseModel):
    """A file attached to a message."""

    model_config = {"arbitrary_types_allowed": True}

    filename: str
    media_type: str  # MIME type
    data: bytes  # raw file content
    size: int
