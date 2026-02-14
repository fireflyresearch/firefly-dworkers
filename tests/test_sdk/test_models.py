"""Tests for SDK request and response models."""

from __future__ import annotations

from firefly_dworkers.sdk.models import (
    ExecutePlanRequest,
    HealthResponse,
    IndexDocumentRequest,
    IndexResponse,
    KnowledgeChunkResponse,
    PlanResponse,
    ProjectEvent,
    RunWorkerRequest,
    SearchKnowledgeRequest,
    SearchResponse,
    StreamEvent,
    WorkerResponse,
)

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TestRequestModels:
    """Test SDK request models."""

    def test_run_worker_request(self) -> None:
        req = RunWorkerRequest(
            worker_role="analyst",
            prompt="Analyze market trends",
            tenant_id="acme",
            conversation_id="conv-123",
            autonomy_level="full",
            model="gpt-4",
        )
        assert req.worker_role == "analyst"
        assert req.prompt == "Analyze market trends"
        assert req.tenant_id == "acme"
        assert req.conversation_id == "conv-123"
        assert req.autonomy_level == "full"
        assert req.model == "gpt-4"

    def test_run_worker_request_defaults(self) -> None:
        req = RunWorkerRequest(worker_role="researcher", prompt="Find papers")
        assert req.tenant_id == "default"
        assert req.conversation_id is None
        assert req.autonomy_level is None
        assert req.model is None

    def test_run_worker_request_exclude_none(self) -> None:
        """exclude_none=True should drop None fields."""
        req = RunWorkerRequest(worker_role="analyst", prompt="test")
        dumped = req.model_dump(exclude_none=True)
        assert "conversation_id" not in dumped
        assert "autonomy_level" not in dumped
        assert "model" not in dumped
        assert dumped["worker_role"] == "analyst"
        assert dumped["prompt"] == "test"

    def test_execute_plan_request(self) -> None:
        req = ExecutePlanRequest(
            plan_name="market-analysis",
            tenant_id="acme",
            inputs={"sector": "tech", "period": "Q4"},
        )
        assert req.plan_name == "market-analysis"
        assert req.tenant_id == "acme"
        assert req.inputs == {"sector": "tech", "period": "Q4"}

    def test_execute_plan_request_defaults(self) -> None:
        req = ExecutePlanRequest(plan_name="simple")
        assert req.tenant_id == "default"
        assert req.inputs == {}

    def test_index_document_request(self) -> None:
        req = IndexDocumentRequest(
            source="report.pdf",
            content="Full text of the report...",
            tenant_id="acme",
            metadata={"author": "Alice"},
            chunk_size=500,
            chunk_overlap=100,
        )
        assert req.source == "report.pdf"
        assert req.content == "Full text of the report..."
        assert req.tenant_id == "acme"
        assert req.metadata == {"author": "Alice"}
        assert req.chunk_size == 500
        assert req.chunk_overlap == 100

    def test_index_document_request_defaults(self) -> None:
        req = IndexDocumentRequest(source="doc.txt", content="Hello")
        assert req.tenant_id == "default"
        assert req.metadata == {}
        assert req.chunk_size == 1000
        assert req.chunk_overlap == 200

    def test_search_knowledge_request(self) -> None:
        req = SearchKnowledgeRequest(query="AI trends", tenant_id="acme", max_results=10)
        assert req.query == "AI trends"
        assert req.tenant_id == "acme"
        assert req.max_results == 10

    def test_search_knowledge_request_defaults(self) -> None:
        req = SearchKnowledgeRequest(query="test")
        assert req.tenant_id == "default"
        assert req.max_results == 5


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TestResponseModels:
    """Test SDK response models."""

    def test_worker_response(self) -> None:
        resp = WorkerResponse(
            worker_name="analyst-01",
            role="analyst",
            output="Analysis complete.",
            conversation_id="conv-123",
        )
        assert resp.worker_name == "analyst-01"
        assert resp.role == "analyst"
        assert resp.output == "Analysis complete."
        assert resp.conversation_id == "conv-123"

    def test_worker_response_minimal(self) -> None:
        resp = WorkerResponse(worker_name="w1", role="researcher", output="done")
        assert resp.conversation_id is None

    def test_plan_response(self) -> None:
        resp = PlanResponse(
            plan_name="market-analysis",
            success=True,
            outputs={"summary": "Good market outlook"},
            duration_ms=1500.5,
        )
        assert resp.plan_name == "market-analysis"
        assert resp.success is True
        assert resp.outputs == {"summary": "Good market outlook"}
        assert resp.duration_ms == 1500.5

    def test_plan_response_defaults(self) -> None:
        resp = PlanResponse(plan_name="test", success=False)
        assert resp.outputs == {}
        assert resp.duration_ms == 0.0

    def test_knowledge_chunk_response(self) -> None:
        resp = KnowledgeChunkResponse(
            chunk_id="chunk-1",
            source="report.pdf",
            content="Excerpt from page 3...",
            metadata={"page": 3},
        )
        assert resp.chunk_id == "chunk-1"
        assert resp.source == "report.pdf"
        assert resp.content == "Excerpt from page 3..."
        assert resp.metadata == {"page": 3}

    def test_knowledge_chunk_response_defaults(self) -> None:
        resp = KnowledgeChunkResponse(chunk_id="c1", source="s", content="c")
        assert resp.metadata == {}

    def test_index_response(self) -> None:
        resp = IndexResponse(chunk_ids=["c1", "c2", "c3"], source="doc.pdf")
        assert resp.chunk_ids == ["c1", "c2", "c3"]
        assert resp.source == "doc.pdf"

    def test_index_response_defaults(self) -> None:
        resp = IndexResponse(source="x.txt")
        assert resp.chunk_ids == []

    def test_search_response(self) -> None:
        chunks = [
            KnowledgeChunkResponse(chunk_id="c1", source="a.pdf", content="text1"),
            KnowledgeChunkResponse(chunk_id="c2", source="b.pdf", content="text2"),
        ]
        resp = SearchResponse(query="AI", results=chunks)
        assert resp.query == "AI"
        assert len(resp.results) == 2
        assert resp.results[0].chunk_id == "c1"

    def test_search_response_defaults(self) -> None:
        resp = SearchResponse(query="empty")
        assert resp.results == []

    def test_health_response(self) -> None:
        resp = HealthResponse(status="ok", version="1.0.0")
        assert resp.status == "ok"
        assert resp.version == "1.0.0"

    def test_health_response_defaults(self) -> None:
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.version == ""


# ---------------------------------------------------------------------------
# Streaming event models
# ---------------------------------------------------------------------------


class TestStreamingEventModels:
    def test_stream_event_token(self):
        e = StreamEvent(type="token", content="Hello")
        assert e.type == "token"
        assert e.content == "Hello"

    def test_stream_event_complete(self):
        e = StreamEvent(type="complete", content="Full output")
        assert e.type == "complete"

    def test_stream_event_error(self):
        e = StreamEvent(type="error", content="Something failed")
        assert e.type == "error"

    def test_stream_event_tool_call(self):
        e = StreamEvent(type="tool_call", content="web_search('query')")
        assert e.type == "tool_call"

    def test_stream_event_metadata(self):
        e = StreamEvent(type="token", content="x", metadata={"key": "val"})
        assert e.metadata == {"key": "val"}

    def test_project_event_worker_output(self):
        e = ProjectEvent(type="worker_output", content="partial result")
        assert e.type == "worker_output"
