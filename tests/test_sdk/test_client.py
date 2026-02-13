"""Tests for SDK sync and async clients using httpx mock transport."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from firefly_dworkers.sdk.async_client import AsyncDworkersClient
from firefly_dworkers.sdk.client import DworkersClient
from firefly_dworkers.sdk.models import (
    ExecutePlanRequest,
    IndexDocumentRequest,
    RunWorkerRequest,
    SearchKnowledgeRequest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(data: Any, status_code: int = 200) -> httpx.Response:
    """Build a mock JSON response."""
    return httpx.Response(
        status_code=status_code,
        json=data,
    )


# ---------------------------------------------------------------------------
# Synchronous client tests
# ---------------------------------------------------------------------------


class TestDworkersClient:
    """Test the synchronous DworkersClient."""

    def _make_client(self, handler) -> DworkersClient:
        """Create a client backed by a mock transport."""
        transport = httpx.MockTransport(handler)
        client = DworkersClient.__new__(DworkersClient)
        client._client = httpx.Client(transport=transport, base_url="http://test")
        return client

    def test_health(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/health"
            return _json_response({"status": "ok", "version": "1.2.3"})

        client = self._make_client(handler)
        resp = client.health()
        assert resp.status == "ok"
        assert resp.version == "1.2.3"

    def test_run_worker(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/workers/run"
            body = json.loads(request.content)
            assert body["worker_role"] == "analyst"
            assert body["prompt"] == "Analyze this"
            # None fields should be excluded
            assert "conversation_id" not in body
            return _json_response(
                {
                    "worker_name": "analyst-01",
                    "role": "analyst",
                    "output": "Analysis complete.",
                    "conversation_id": "conv-abc",
                }
            )

        client = self._make_client(handler)
        resp = client.run_worker(RunWorkerRequest(worker_role="analyst", prompt="Analyze this"))
        assert resp.worker_name == "analyst-01"
        assert resp.role == "analyst"
        assert resp.output == "Analysis complete."
        assert resp.conversation_id == "conv-abc"

    def test_execute_plan(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/plans/execute"
            body = json.loads(request.content)
            assert body["plan_name"] == "market-analysis"
            assert body["inputs"] == {"sector": "tech"}
            return _json_response(
                {
                    "plan_name": "market-analysis",
                    "success": True,
                    "outputs": {"summary": "Done"},
                    "duration_ms": 1234.5,
                }
            )

        client = self._make_client(handler)
        resp = client.execute_plan(
            ExecutePlanRequest(plan_name="market-analysis", inputs={"sector": "tech"}),
        )
        assert resp.plan_name == "market-analysis"
        assert resp.success is True
        assert resp.outputs == {"summary": "Done"}
        assert resp.duration_ms == 1234.5

    def test_index_document(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/knowledge/index"
            body = json.loads(request.content)
            assert body["source"] == "report.pdf"
            assert body["content"] == "Full report text"
            return _json_response({"chunk_ids": ["c1", "c2"], "source": "report.pdf"})

        client = self._make_client(handler)
        resp = client.index_document(
            IndexDocumentRequest(source="report.pdf", content="Full report text"),
        )
        assert resp.chunk_ids == ["c1", "c2"]
        assert resp.source == "report.pdf"

    def test_search_knowledge(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/knowledge/search"
            body = json.loads(request.content)
            assert body["query"] == "AI trends"
            return _json_response(
                {
                    "query": "AI trends",
                    "results": [
                        {"chunk_id": "c1", "source": "a.pdf", "content": "AI is growing"},
                    ],
                }
            )

        client = self._make_client(handler)
        resp = client.search_knowledge(SearchKnowledgeRequest(query="AI trends"))
        assert resp.query == "AI trends"
        assert len(resp.results) == 1
        assert resp.results[0].chunk_id == "c1"

    def test_list_plans(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/plans"
            return _json_response(["market-analysis", "due-diligence"])

        client = self._make_client(handler)
        plans = client.list_plans()
        assert plans == ["market-analysis", "due-diligence"]

    def test_list_workers(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/workers"
            return _json_response(["analyst", "researcher", "data_analyst", "manager"])

        client = self._make_client(handler)
        workers = client.list_workers()
        assert workers == ["analyst", "researcher", "data_analyst", "manager"]

    def test_context_manager(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response({"status": "ok", "version": ""})

        transport = httpx.MockTransport(handler)
        with DworkersClient.__new__(DworkersClient) as client:
            client._client = httpx.Client(transport=transport, base_url="http://test")
            resp = client.health()
            assert resp.status == "ok"

    def test_api_key_header(self) -> None:
        """Verify that api_key is sent as Bearer token."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers.get("authorization") == "Bearer secret-key"
            return _json_response({"status": "ok", "version": ""})

        transport = httpx.MockTransport(handler)
        client = DworkersClient.__new__(DworkersClient)
        client._client = httpx.Client(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer secret-key"},
        )
        resp = client.health()
        assert resp.status == "ok"

    def test_api_key_in_constructor(self) -> None:
        """Verify the constructor sets the auth header correctly."""
        client = DworkersClient(base_url="http://localhost:9999", api_key="my-key")
        assert client._client.headers.get("authorization") == "Bearer my-key"
        client.close()

    def test_constructor_defaults(self) -> None:
        """Verify constructor defaults work."""
        client = DworkersClient()
        assert "authorization" not in client._client.headers
        client.close()

    def test_http_error_raises(self) -> None:
        """Verify that HTTP errors propagate as httpx.HTTPStatusError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=500, json={"detail": "Internal error"})

        client = self._make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            client.health()


# ---------------------------------------------------------------------------
# Async client tests
# ---------------------------------------------------------------------------


class TestAsyncDworkersClient:
    """Test the asynchronous AsyncDworkersClient."""

    def _make_client(self, handler) -> AsyncDworkersClient:
        """Create an async client backed by a mock transport."""
        transport = httpx.MockTransport(handler)
        client = AsyncDworkersClient.__new__(AsyncDworkersClient)
        client._client = httpx.AsyncClient(transport=transport, base_url="http://test")
        return client

    async def test_health(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response({"status": "ok", "version": "2.0.0"})

        client = self._make_client(handler)
        resp = await client.health()
        assert resp.status == "ok"
        assert resp.version == "2.0.0"
        await client.close()

    async def test_run_worker(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/workers/run"
            body = json.loads(request.content)
            assert body["worker_role"] == "researcher"
            return _json_response(
                {
                    "worker_name": "researcher-01",
                    "role": "researcher",
                    "output": "Research complete.",
                }
            )

        client = self._make_client(handler)
        resp = await client.run_worker(RunWorkerRequest(worker_role="researcher", prompt="Find papers"))
        assert resp.worker_name == "researcher-01"
        assert resp.output == "Research complete."
        await client.close()

    async def test_execute_plan(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(
                {
                    "plan_name": "due-diligence",
                    "success": True,
                    "outputs": {},
                    "duration_ms": 500.0,
                }
            )

        client = self._make_client(handler)
        resp = await client.execute_plan(ExecutePlanRequest(plan_name="due-diligence"))
        assert resp.plan_name == "due-diligence"
        assert resp.success is True
        await client.close()

    async def test_index_document(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response({"chunk_ids": ["c1"], "source": "doc.txt"})

        client = self._make_client(handler)
        resp = await client.index_document(IndexDocumentRequest(source="doc.txt", content="Hello"))
        assert resp.chunk_ids == ["c1"]
        assert resp.source == "doc.txt"
        await client.close()

    async def test_search_knowledge(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response({"query": "test", "results": []})

        client = self._make_client(handler)
        resp = await client.search_knowledge(SearchKnowledgeRequest(query="test"))
        assert resp.query == "test"
        assert resp.results == []
        await client.close()

    async def test_list_plans(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(["plan-a", "plan-b"])

        client = self._make_client(handler)
        plans = await client.list_plans()
        assert plans == ["plan-a", "plan-b"]
        await client.close()

    async def test_list_workers(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(["analyst", "researcher"])

        client = self._make_client(handler)
        workers = await client.list_workers()
        assert workers == ["analyst", "researcher"]
        await client.close()

    async def test_context_manager(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response({"status": "ok", "version": ""})

        transport = httpx.MockTransport(handler)
        client = AsyncDworkersClient.__new__(AsyncDworkersClient)
        client._client = httpx.AsyncClient(transport=transport, base_url="http://test")

        async with client as c:
            resp = await c.health()
            assert resp.status == "ok"

    async def test_api_key_in_constructor(self) -> None:
        """Verify the async constructor sets the auth header correctly."""
        client = AsyncDworkersClient(base_url="http://localhost:9999", api_key="async-key")
        assert client._client.headers.get("authorization") == "Bearer async-key"
        await client.close()

    async def test_constructor_defaults(self) -> None:
        """Verify async constructor defaults work."""
        client = AsyncDworkersClient()
        assert "authorization" not in client._client.headers
        await client.close()

    async def test_http_error_raises(self) -> None:
        """Verify that HTTP errors propagate as httpx.HTTPStatusError."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=404, json={"detail": "Not found"})

        client = self._make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await client.health()
        await client.close()
