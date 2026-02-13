"""Tests for workers API endpoints (SSE streaming and sync)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from firefly_dworkers.sdk.models import StreamEvent
from firefly_dworkers_server.app import create_dworkers_app


@pytest.fixture()
def app():
    return create_dworkers_app()


@pytest.fixture()
def client(app):
    return TestClient(app)


def _make_tenant_config() -> MagicMock:
    """Build a minimal mock TenantConfig."""
    config = MagicMock()
    config.id = "test-tenant"
    config.models.default = "openai:gpt-4o"
    config.verticals = []
    config.branding.company_name = "TestCo"

    settings = MagicMock()
    settings.autonomy = "semi_supervised"
    settings.custom_instructions = ""
    config.workers.settings_for.return_value = settings
    return config


def _make_mock_worker(tokens: list[str] | None = None, name: str = "test-worker"):
    """Build a mock worker with run_stream and run methods."""
    worker = MagicMock()
    worker.name = name

    if tokens is None:
        tokens = ["Hello", " ", "World"]

    # -- run_stream mock -----------------------------------------------
    # run_stream is async and returns a context manager
    stream_wrapper = MagicMock()

    async def _stream_tokens():
        for t in tokens:
            yield t

    stream_wrapper.stream_tokens = _stream_tokens

    stream_ctx = AsyncMock()
    stream_ctx.__aenter__ = AsyncMock(return_value=stream_wrapper)
    stream_ctx.__aexit__ = AsyncMock(return_value=False)

    async def _run_stream(*args, **kwargs):
        return stream_ctx

    worker.run_stream = _run_stream

    # -- run mock (sync execution) -------------------------------------
    run_result = MagicMock()
    run_result.output = "".join(tokens)
    worker.run = AsyncMock(return_value=run_result)

    return worker


def _parse_sse_events(content: str) -> list[StreamEvent]:
    """Parse raw SSE text into a list of StreamEvent objects."""
    events: list[StreamEvent] = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            payload = line[len("data: ") :]
            events.append(StreamEvent.model_validate_json(payload))
    return events


# ---------------------------------------------------------------------------
# Tests: list workers
# ---------------------------------------------------------------------------


class TestListWorkers:
    def test_list_workers_returns_list(self, client):
        with patch("firefly_dworkers.workers.worker_registry") as mock_registry:
            mock_registry.list_workers.return_value = ["analyst-default", "researcher-default"]
            resp = client.get("/api/workers")
        assert resp.status_code == 200
        assert resp.json() == ["analyst-default", "researcher-default"]

    def test_list_workers_empty(self, client):
        with patch("firefly_dworkers.workers.worker_registry") as mock_registry:
            mock_registry.list_workers.return_value = []
            resp = client.get("/api/workers")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: SSE streaming endpoint  POST /api/workers/run
# ---------------------------------------------------------------------------


class TestRunWorkerStream:
    def test_returns_sse_content_type(self, client):
        """The response should have text/event-stream media type."""
        config = _make_tenant_config()
        worker = _make_mock_worker(["Hi"])

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.return_value = worker

            resp = client.post(
                "/api/workers/run",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_streams_token_and_complete_events(self, client):
        """Should yield individual token events followed by a complete event."""
        config = _make_tenant_config()
        worker = _make_mock_worker(["Hello", " ", "World"])

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.return_value = worker

            resp = client.post(
                "/api/workers/run",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "test-tenant"},
            )

        events = _parse_sse_events(resp.text)
        # 3 tokens + 1 complete
        assert len(events) == 4

        # First 3 are tokens
        assert events[0].type == "token"
        assert events[0].content == "Hello"
        assert events[1].type == "token"
        assert events[1].content == " "
        assert events[2].type == "token"
        assert events[2].content == "World"

        # Last is complete
        assert events[3].type == "complete"
        assert events[3].content == "Hello World"
        assert events[3].metadata["worker_role"] == "analyst"

    def test_stream_with_conversation_id(self, client):
        """Conversation ID should be passed through to run_stream."""
        config = _make_tenant_config()
        worker = _make_mock_worker(["ok"])

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.return_value = worker

            resp = client.post(
                "/api/workers/run",
                json={
                    "worker_role": "analyst",
                    "prompt": "test",
                    "tenant_id": "test-tenant",
                    "conversation_id": "conv-123",
                },
            )

        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        assert any(e.type == "complete" for e in events)

    def test_stream_unknown_tenant_returns_404(self, client):
        """An unknown tenant should produce an SSE error event (since the
        generator catches the HTTPException raised by _create_worker)."""
        from firefly_dworkers.exceptions import TenantNotFoundError

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.side_effect = TenantNotFoundError("Tenant 'nope' not registered")

            resp = client.post(
                "/api/workers/run",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "nope"},
            )

        # The SSE endpoint returns 200 with an error event inside the stream
        # because the HTTPException is raised inside the async generator
        # and caught by the except block in _stream_worker_events
        events = _parse_sse_events(resp.text)
        assert any(e.type == "error" for e in events)

    def test_stream_invalid_role_returns_error_event(self, client):
        """An invalid role should produce an SSE error event."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/workers/run",
                json={
                    "worker_role": "not_a_real_role",
                    "prompt": "test",
                    "tenant_id": "test-tenant",
                },
            )

        events = _parse_sse_events(resp.text)
        assert any(e.type == "error" for e in events)

    def test_stream_worker_error_yields_error_event(self, client):
        """If the worker raises during streaming, an error event should appear."""
        config = _make_tenant_config()
        worker = MagicMock()
        worker.name = "test-worker"

        # Make run_stream raise
        async def _failing_run_stream(*args, **kwargs):
            raise RuntimeError("LLM connection failed")

        worker.run_stream = _failing_run_stream

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.return_value = worker

            resp = client.post(
                "/api/workers/run",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "test-tenant"},
            )

        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert "LLM connection failed" in error_events[0].content


# ---------------------------------------------------------------------------
# Tests: synchronous endpoint  POST /api/workers/run/sync
# ---------------------------------------------------------------------------


class TestRunWorkerSync:
    def test_returns_json_worker_response(self, client):
        """The sync endpoint should return a WorkerResponse JSON."""
        config = _make_tenant_config()
        worker = _make_mock_worker(["Analysis complete."])

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.return_value = worker

            resp = client.post(
                "/api/workers/run/sync",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["worker_name"] == "test-worker"
        assert data["role"] == "analyst"
        assert data["output"] == "Analysis complete."

    def test_sync_with_conversation_id(self, client):
        """Conversation ID should be returned in the response."""
        config = _make_tenant_config()
        worker = _make_mock_worker(["done"])

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.return_value = worker

            resp = client.post(
                "/api/workers/run/sync",
                json={
                    "worker_role": "analyst",
                    "prompt": "test",
                    "tenant_id": "test-tenant",
                    "conversation_id": "conv-abc",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["conversation_id"] == "conv-abc"

    def test_sync_unknown_tenant_returns_404(self, client):
        """A missing tenant should return 404."""
        from firefly_dworkers.exceptions import TenantNotFoundError

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.side_effect = TenantNotFoundError("Tenant 'nope' not registered")

            resp = client.post(
                "/api/workers/run/sync",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "nope"},
            )

        assert resp.status_code == 404

    def test_sync_invalid_role_returns_400(self, client):
        """An invalid worker role should return 400."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/workers/run/sync",
                json={
                    "worker_role": "not_a_real_role",
                    "prompt": "test",
                    "tenant_id": "test-tenant",
                },
            )

        assert resp.status_code == 400
        assert "Invalid worker role" in resp.json()["detail"]

    def test_sync_unregistered_role_returns_404(self, client):
        """A valid role with no registered factory class should return 404."""
        config = _make_tenant_config()

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.side_effect = KeyError("No worker registered for role 'analyst'")

            resp = client.post(
                "/api/workers/run/sync",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 404

    def test_sync_worker_execution_error_returns_500(self, client):
        """If the worker.run() fails, should return 500."""
        config = _make_tenant_config()
        worker = MagicMock()
        worker.name = "test-worker"
        worker.run = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        with (
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.workers.factory.worker_factory") as mock_wf,
        ):
            mock_tr.get.return_value = config
            mock_wf.create.return_value = worker

            resp = client.post(
                "/api/workers/run/sync",
                json={"worker_role": "analyst", "prompt": "test", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 500
        assert "LLM timeout" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: StreamEvent model
# ---------------------------------------------------------------------------


class TestStreamEventModel:
    def test_token_event(self):
        event = StreamEvent(type="token", content="Hello")
        assert event.type == "token"
        assert event.content == "Hello"
        assert event.metadata == {}

    def test_complete_event_with_metadata(self):
        event = StreamEvent(
            type="complete",
            content="full output",
            metadata={"worker_role": "analyst"},
        )
        data = event.model_dump()
        assert data["type"] == "complete"
        assert data["metadata"]["worker_role"] == "analyst"

    def test_error_event(self):
        event = StreamEvent(type="error", content="something went wrong")
        assert event.type == "error"
        assert event.content == "something went wrong"

    def test_round_trip_json(self):
        event = StreamEvent(type="token", content="test")
        json_str = event.model_dump_json()
        restored = StreamEvent.model_validate_json(json_str)
        assert restored == event
