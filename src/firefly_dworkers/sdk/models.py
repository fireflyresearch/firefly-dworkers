"""SDK request and response models for the dworkers API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class FileAttachmentPayload(BaseModel):
    """File attachment in API request (base64-encoded)."""

    filename: str
    media_type: str
    data_b64: str  # base64-encoded file content


class RunWorkerRequest(BaseModel):
    """Request to run a digital worker."""

    worker_role: str  # "analyst", "researcher", "data_analyst", "manager"
    prompt: str
    tenant_id: str = "default"
    conversation_id: str | None = None
    autonomy_level: str | None = None  # override
    model: str | None = None  # override
    attachments: list[FileAttachmentPayload] = Field(default_factory=list)


class ExecutePlanRequest(BaseModel):
    """Request to execute a consulting plan."""

    plan_name: str
    tenant_id: str = "default"
    inputs: dict[str, Any] = Field(default_factory=dict)


class IndexDocumentRequest(BaseModel):
    """Request to index a document into knowledge base."""

    source: str
    content: str
    tenant_id: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size: int = 1000
    chunk_overlap: int = 200


class SearchKnowledgeRequest(BaseModel):
    """Request to search the knowledge base."""

    query: str
    tenant_id: str = "default"
    max_results: int = 5


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class WorkerResponse(BaseModel):
    """Response from a worker run."""

    worker_name: str
    role: str
    output: str
    conversation_id: str | None = None


class PlanResponse(BaseModel):
    """Response from a plan execution."""

    plan_name: str
    success: bool
    outputs: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


class KnowledgeChunkResponse(BaseModel):
    """A knowledge chunk in search results."""

    chunk_id: str
    source: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexResponse(BaseModel):
    """Response from indexing a document."""

    chunk_ids: list[str] = Field(default_factory=list)
    source: str


class SearchResponse(BaseModel):
    """Response from a knowledge search."""

    query: str
    results: list[KnowledgeChunkResponse] = Field(default_factory=list)


class StreamEvent(BaseModel):
    """A single SSE event from a streaming worker execution.

    Event types:
    - ``"token"``: An incremental text token from the worker.
    - ``"tool_call"``: A tool invocation by the worker (content is the tool description).
    - ``"complete"``: The full output after all tokens have been streamed.
    - ``"error"``: An error that occurred during worker execution.
    """

    type: str  # "token", "tool_call", "complete", "error"
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectRequest(BaseModel):
    """Request to run a multi-agent project."""

    brief: str
    tenant_id: str = "default"
    project_id: str | None = None  # auto-generated if not provided
    worker_roles: list[str] = Field(default_factory=list)  # optional override


class ProjectEvent(BaseModel):
    """An event from project orchestration.

    Event types:
    - ``"project_start"``: Project orchestration has begun.
    - ``"task_assigned"``: A task has been assigned to a worker.
    - ``"task_complete"``: A worker has completed a task.
    - ``"worker_output"``: Incremental output from a worker.
    - ``"project_complete"``: The entire project has finished.
    - ``"error"``: An error occurred during orchestration.
    """

    type: str
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectResponse(BaseModel):
    """Response from a synchronous project run."""

    project_id: str
    success: bool
    deliverables: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = ""
