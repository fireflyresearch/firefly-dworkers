"""Tests for projects API endpoints (SSE streaming and sync execution)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from firefly_dworkers.sdk.models import ProjectEvent, ProjectRequest, ProjectResponse
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


def _parse_sse_events(content: str) -> list[ProjectEvent]:
    """Parse raw SSE text into a list of ProjectEvent objects."""
    events: list[ProjectEvent] = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            payload = line[len("data: ") :]
            events.append(ProjectEvent.model_validate_json(payload))
    return events


# ---------------------------------------------------------------------------
# Tests: ProjectEvent and ProjectRequest model validation
# ---------------------------------------------------------------------------


class TestProjectModels:
    def test_project_request_minimal(self):
        """ProjectRequest should only require brief."""
        req = ProjectRequest(brief="Build a market analysis")
        assert req.brief == "Build a market analysis"
        assert req.tenant_id == "default"
        assert req.project_id is None
        assert req.worker_roles == []

    def test_project_request_full(self):
        """ProjectRequest should accept all fields."""
        req = ProjectRequest(
            brief="Analyze competitors",
            tenant_id="acme",
            project_id="proj-123",
            worker_roles=["analyst", "researcher"],
        )
        assert req.brief == "Analyze competitors"
        assert req.tenant_id == "acme"
        assert req.project_id == "proj-123"
        assert req.worker_roles == ["analyst", "researcher"]

    def test_project_event_defaults(self):
        """ProjectEvent content and metadata should have defaults."""
        event = ProjectEvent(type="project_start")
        assert event.type == "project_start"
        assert event.content == ""
        assert event.metadata == {}

    def test_project_event_with_metadata(self):
        """ProjectEvent should accept metadata."""
        event = ProjectEvent(
            type="task_assigned",
            content="step-1",
            metadata={"worker": "analyst", "task": "research"},
        )
        data = event.model_dump()
        assert data["type"] == "task_assigned"
        assert data["metadata"]["worker"] == "analyst"

    def test_project_event_round_trip_json(self):
        """ProjectEvent should survive JSON round-trip."""
        event = ProjectEvent(
            type="worker_output",
            content="partial results",
            metadata={"step": 1},
        )
        json_str = event.model_dump_json()
        restored = ProjectEvent.model_validate_json(json_str)
        assert restored == event

    def test_project_response_defaults(self):
        """ProjectResponse should have sensible defaults."""
        resp = ProjectResponse(project_id="proj-1", success=True)
        assert resp.project_id == "proj-1"
        assert resp.success is True
        assert resp.deliverables == {}
        assert resp.duration_ms == 0.0

    def test_project_response_full(self):
        """ProjectResponse should accept all fields."""
        resp = ProjectResponse(
            project_id="proj-2",
            success=True,
            deliverables={"report": "content here"},
            duration_ms=1234.5,
        )
        assert resp.deliverables["report"] == "content here"
        assert resp.duration_ms == 1234.5


# ---------------------------------------------------------------------------
# Tests: SSE streaming endpoint  POST /api/projects/run
# ---------------------------------------------------------------------------


class TestRunProjectStream:
    def test_returns_sse_content_type(self, client):
        """The response should have text/event-stream media type."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run",
                json={"brief": "Build a market analysis", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_streams_placeholder_events(self, client):
        """Without ProjectOrchestrator, should yield project_start and project_complete."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run",
                json={"brief": "Build a market analysis", "tenant_id": "test-tenant"},
            )

        events = _parse_sse_events(resp.text)
        assert len(events) == 2

        assert events[0].type == "project_start"
        assert events[0].metadata["brief"] == "Build a market analysis"

        assert events[1].type == "project_complete"
        assert events[1].metadata["success"] is True
        assert "not yet implemented" in events[1].metadata["note"].lower()

    def test_auto_generated_project_id(self, client):
        """When no project_id is provided, one should be auto-generated."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run",
                json={"brief": "test brief", "tenant_id": "test-tenant"},
            )

        events = _parse_sse_events(resp.text)
        project_id = events[0].content
        # UUID4 format: 8-4-4-4-12 hex chars
        assert len(project_id) == 36
        assert project_id.count("-") == 4

    def test_custom_project_id_passthrough(self, client):
        """When a project_id is provided, it should be used as-is."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run",
                json={
                    "brief": "test brief",
                    "tenant_id": "test-tenant",
                    "project_id": "my-custom-id",
                },
            )

        events = _parse_sse_events(resp.text)
        assert events[0].content == "my-custom-id"

    def test_stream_unknown_tenant_yields_error_event(self, client):
        """An unknown tenant should produce an SSE error event."""
        from firefly_dworkers.exceptions import TenantNotFoundError

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.side_effect = TenantNotFoundError("Tenant 'nope' not registered")

            resp = client.post(
                "/api/projects/run",
                json={"brief": "test", "tenant_id": "nope"},
            )

        # SSE endpoint returns 200 with error events in the stream
        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert "nope" in error_events[0].content

    def test_stream_brief_truncated_in_metadata(self, client):
        """Long briefs should be truncated to 200 chars in the start event metadata."""
        config = _make_tenant_config()
        long_brief = "x" * 500

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run",
                json={"brief": long_brief, "tenant_id": "test-tenant"},
            )

        events = _parse_sse_events(resp.text)
        start_event = events[0]
        assert len(start_event.metadata["brief"]) == 200

    def test_stream_project_start_and_complete_share_project_id(self, client):
        """Both start and complete events should reference the same project_id."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run",
                json={
                    "brief": "test",
                    "tenant_id": "test-tenant",
                    "project_id": "proj-abc",
                },
            )

        events = _parse_sse_events(resp.text)
        assert events[0].content == "proj-abc"
        assert events[1].content == "proj-abc"


# ---------------------------------------------------------------------------
# Tests: synchronous endpoint  POST /api/projects/run/sync
# ---------------------------------------------------------------------------


class TestRunProjectSync:
    def test_returns_project_response_json(self, client):
        """The sync endpoint should return a ProjectResponse JSON."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run/sync",
                json={"brief": "test brief", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "project_id" in data
        assert "note" in data["deliverables"]

    def test_sync_custom_project_id(self, client):
        """A custom project_id should be returned in the response."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run/sync",
                json={
                    "brief": "test",
                    "tenant_id": "test-tenant",
                    "project_id": "my-proj",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["project_id"] == "my-proj"

    def test_sync_auto_generated_project_id(self, client):
        """When no project_id is provided, one should be auto-generated."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run/sync",
                json={"brief": "test", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 200
        project_id = resp.json()["project_id"]
        assert len(project_id) == 36
        assert project_id.count("-") == 4

    def test_sync_unknown_tenant_returns_404(self, client):
        """A missing tenant should return 404."""
        from firefly_dworkers.exceptions import TenantNotFoundError

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.side_effect = TenantNotFoundError("Tenant 'nope' not registered")

            resp = client.post(
                "/api/projects/run/sync",
                json={"brief": "test", "tenant_id": "nope"},
            )

        assert resp.status_code == 404
        assert "nope" in resp.json()["detail"]

    def test_sync_placeholder_deliverables(self, client):
        """Without orchestrator, deliverables should contain a 'not yet implemented' note."""
        config = _make_tenant_config()

        with patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr:
            mock_tr.get.return_value = config

            resp = client.post(
                "/api/projects/run/sync",
                json={"brief": "test brief", "tenant_id": "test-tenant"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "not yet implemented" in data["deliverables"]["note"].lower()

    def test_sync_missing_brief_returns_422(self, client):
        """A request without 'brief' should return 422 (validation error)."""
        resp = client.post(
            "/api/projects/run/sync",
            json={"tenant_id": "test-tenant"},
        )
        assert resp.status_code == 422
