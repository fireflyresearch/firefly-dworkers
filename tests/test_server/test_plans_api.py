"""Tests for plans API endpoints (SSE streaming and sync execution)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fireflyframework_genai.pipeline.result import NodeResult, PipelineResult

from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.sdk.models import StreamEvent
from firefly_dworkers.types import WorkerRole
from firefly_dworkers_server.app import create_dworkers_app


@pytest.fixture()
def app():
    return create_dworkers_app()


@pytest.fixture()
def client(app):
    return TestClient(app)


def _make_plan() -> BasePlan:
    """Build a minimal plan for testing."""
    return BasePlan(
        name="test-plan",
        description="A test plan for unit tests",
        steps=[
            PlanStep(
                step_id="step1",
                name="Research",
                description="Gather data",
                worker_role=WorkerRole.RESEARCHER,
            ),
            PlanStep(
                step_id="step2",
                name="Analyze",
                description="Analyze data",
                worker_role=WorkerRole.ANALYST,
                depends_on=["step1"],
            ),
        ],
    )


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


def _make_pipeline_result(success: bool = True) -> PipelineResult:
    """Build a mock PipelineResult."""
    return PipelineResult(
        pipeline_name="test-plan",
        outputs={
            "step1": NodeResult(node_id="step1", output="research results", success=True, latency_ms=100.0),
            "step2": NodeResult(node_id="step2", output="analysis results", success=True, latency_ms=200.0),
        },
        final_output="analysis results",
        execution_trace=[],
        total_duration_ms=300.0,
        success=success,
    )


def _make_mock_pipeline(
    result: PipelineResult | None = None,
    *,
    fire_events: bool = False,
) -> MagicMock:
    """Build a mock PipelineEngine.

    Parameters:
        result: The PipelineResult to return from run().
        fire_events: If True, the mock run() will call the event handler
            methods to simulate real pipeline events.
    """
    if result is None:
        result = _make_pipeline_result()

    pipeline = MagicMock()
    pipeline._event_handler = None

    async def _mock_run(inputs=None, context=None):
        handler = pipeline._event_handler
        if fire_events and handler is not None:
            # Simulate pipeline event flow
            await handler.on_node_start("step1", "test-plan")
            await handler.on_node_complete("step1", "test-plan", 100.0)
            await handler.on_node_start("step2", "test-plan")
            await handler.on_node_complete("step2", "test-plan", 200.0)
            await handler.on_pipeline_complete("test-plan", result.success, result.total_duration_ms)
        return result

    pipeline.run = _mock_run
    return pipeline


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
# Tests: list plans  GET /api/plans
# ---------------------------------------------------------------------------


class TestListPlans:
    def test_list_plans_returns_list(self, client):
        with patch("firefly_dworkers.plans.plan_registry") as mock_registry:
            mock_registry.list_plans.return_value = ["plan-a", "plan-b"]
            resp = client.get("/api/plans")
        assert resp.status_code == 200
        assert resp.json() == ["plan-a", "plan-b"]

    def test_list_plans_empty(self, client):
        with patch("firefly_dworkers.plans.plan_registry") as mock_registry:
            mock_registry.list_plans.return_value = []
            resp = client.get("/api/plans")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Tests: get plan  GET /api/plans/{plan_name}
# ---------------------------------------------------------------------------


class TestGetPlan:
    def test_get_plan_returns_details(self, client):
        plan = _make_plan()
        with patch("firefly_dworkers.plans.plan_registry") as mock_registry:
            mock_registry.get.return_value = plan
            resp = client.get("/api/plans/test-plan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test-plan"
        assert data["description"] == "A test plan for unit tests"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["step_id"] == "step1"
        assert data["steps"][1]["step_id"] == "step2"

    def test_get_plan_not_found(self, client):
        from firefly_dworkers.exceptions import PlanNotFoundError

        with patch("firefly_dworkers.plans.plan_registry") as mock_registry:
            mock_registry.get.side_effect = PlanNotFoundError("Plan 'nope' not found")
            resp = client.get("/api/plans/nope")
        assert resp.status_code == 404
        assert "nope" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: SSE streaming execution  POST /api/plans/execute
# ---------------------------------------------------------------------------


class TestExecutePlanStream:
    def test_returns_sse_content_type(self, client):
        """The response should have text/event-stream media type."""
        plan = _make_plan()
        config = _make_tenant_config()
        pipeline = _make_mock_pipeline(fire_events=True)

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.plans.builder.PlanBuilder") as mock_pb_cls,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.return_value = config
            mock_pb_cls.return_value.build.return_value = pipeline

            resp = client.post(
                "/api/plans/execute",
                json={"plan_name": "test-plan", "tenant_id": "test-tenant", "inputs": {}},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_streams_node_and_pipeline_events(self, client):
        """Should yield node_start, node_complete, and pipeline_complete events."""
        plan = _make_plan()
        config = _make_tenant_config()
        pipeline = _make_mock_pipeline(fire_events=True)

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.plans.builder.PlanBuilder") as mock_pb_cls,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.return_value = config
            mock_pb_cls.return_value.build.return_value = pipeline

            resp = client.post(
                "/api/plans/execute",
                json={"plan_name": "test-plan", "tenant_id": "test-tenant", "inputs": {}},
            )

        events = _parse_sse_events(resp.text)

        # Should have: node_start(step1), node_complete(step1),
        #              node_start(step2), node_complete(step2),
        #              pipeline_complete
        assert len(events) == 5

        assert events[0].type == "node_start"
        assert events[0].content == "step1"

        assert events[1].type == "node_complete"
        assert events[1].content == "step1"
        assert events[1].metadata["latency_ms"] == 100.0

        assert events[2].type == "node_start"
        assert events[2].content == "step2"

        assert events[3].type == "node_complete"
        assert events[3].content == "step2"
        assert events[3].metadata["latency_ms"] == 200.0

        assert events[4].type == "pipeline_complete"
        assert events[4].metadata["success"] is True
        assert events[4].metadata["duration_ms"] == 300.0

    def test_unknown_plan_yields_error_event(self, client):
        """An unknown plan should produce an SSE error event."""
        from firefly_dworkers.exceptions import PlanNotFoundError

        with patch("firefly_dworkers.plans.plan_registry") as mock_pr:
            mock_pr.get.side_effect = PlanNotFoundError("Plan 'nope' not found")

            resp = client.post(
                "/api/plans/execute",
                json={"plan_name": "nope", "tenant_id": "test-tenant", "inputs": {}},
            )

        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert "nope" in error_events[0].content

    def test_unknown_tenant_yields_error_event(self, client):
        """An unknown tenant should produce an SSE error event."""
        from firefly_dworkers.exceptions import TenantNotFoundError

        plan = _make_plan()

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.side_effect = TenantNotFoundError("Tenant 'nope' not registered")

            resp = client.post(
                "/api/plans/execute",
                json={"plan_name": "test-plan", "tenant_id": "nope", "inputs": {}},
            )

        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert "nope" in error_events[0].content

    def test_pipeline_error_yields_error_event(self, client):
        """If the pipeline raises during execution, an error event should appear."""
        plan = _make_plan()
        config = _make_tenant_config()

        pipeline = MagicMock()
        pipeline._event_handler = None

        async def _failing_run(inputs=None, context=None):
            raise RuntimeError("Pipeline exploded")

        pipeline.run = _failing_run

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.plans.builder.PlanBuilder") as mock_pb_cls,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.return_value = config
            mock_pb_cls.return_value.build.return_value = pipeline

            resp = client.post(
                "/api/plans/execute",
                json={"plan_name": "test-plan", "tenant_id": "test-tenant", "inputs": {}},
            )

        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert "Pipeline exploded" in error_events[0].content

    def test_inputs_are_passed_to_pipeline(self, client):
        """The inputs from the request should be passed to pipeline.run()."""
        plan = _make_plan()
        config = _make_tenant_config()

        captured_inputs = {}
        pipeline = MagicMock()
        pipeline._event_handler = None

        async def _capturing_run(inputs=None, context=None):
            captured_inputs["value"] = inputs
            handler = pipeline._event_handler
            if handler is not None:
                await handler.on_pipeline_complete("test-plan", True, 100.0)
            return _make_pipeline_result()

        pipeline.run = _capturing_run

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.plans.builder.PlanBuilder") as mock_pb_cls,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.return_value = config
            mock_pb_cls.return_value.build.return_value = pipeline

            resp = client.post(
                "/api/plans/execute",
                json={"plan_name": "test-plan", "tenant_id": "test-tenant", "inputs": {"company": "Acme"}},
            )

        assert resp.status_code == 200
        assert captured_inputs["value"] == {"company": "Acme"}


# ---------------------------------------------------------------------------
# Tests: sync execution  POST /api/plans/execute/sync
# ---------------------------------------------------------------------------


class TestExecutePlanSync:
    def test_returns_plan_response(self, client):
        """The sync endpoint should return a PlanResponse JSON."""
        plan = _make_plan()
        config = _make_tenant_config()
        result = _make_pipeline_result()
        pipeline = _make_mock_pipeline(result)

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.plans.builder.PlanBuilder") as mock_pb_cls,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.return_value = config
            mock_pb_cls.return_value.build.return_value = pipeline

            resp = client.post(
                "/api/plans/execute/sync",
                json={"plan_name": "test-plan", "tenant_id": "test-tenant", "inputs": {}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_name"] == "test-plan"
        assert data["success"] is True
        assert data["duration_ms"] == 300.0
        # Only successful nodes have their output in the response
        assert "step1" in data["outputs"]
        assert "step2" in data["outputs"]

    def test_sync_not_found_returns_404(self, client):
        """A missing plan should return 404."""
        from firefly_dworkers.exceptions import PlanNotFoundError

        with patch("firefly_dworkers.plans.plan_registry") as mock_pr:
            mock_pr.get.side_effect = PlanNotFoundError("Plan 'nope' not found")

            resp = client.post(
                "/api/plans/execute/sync",
                json={"plan_name": "nope", "tenant_id": "test-tenant", "inputs": {}},
            )

        assert resp.status_code == 404
        assert "nope" in resp.json()["detail"]

    def test_sync_unknown_tenant_returns_404(self, client):
        """A missing tenant should return 404."""
        from firefly_dworkers.exceptions import TenantNotFoundError

        plan = _make_plan()

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.side_effect = TenantNotFoundError("Tenant 'nope' not registered")

            resp = client.post(
                "/api/plans/execute/sync",
                json={"plan_name": "test-plan", "tenant_id": "nope", "inputs": {}},
            )

        assert resp.status_code == 404
        assert "nope" in resp.json()["detail"]

    def test_sync_pipeline_error_returns_500(self, client):
        """If the pipeline raises, should return 500."""
        plan = _make_plan()
        config = _make_tenant_config()

        pipeline = MagicMock()

        async def _failing_run(inputs=None, context=None):
            raise RuntimeError("LLM timeout")

        pipeline.run = _failing_run

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.plans.builder.PlanBuilder") as mock_pb_cls,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.return_value = config
            mock_pb_cls.return_value.build.return_value = pipeline

            resp = client.post(
                "/api/plans/execute/sync",
                json={"plan_name": "test-plan", "tenant_id": "test-tenant", "inputs": {}},
            )

        assert resp.status_code == 500
        assert "LLM timeout" in resp.json()["detail"]

    def test_sync_passes_inputs(self, client):
        """The inputs from the request should be forwarded to pipeline.run()."""
        plan = _make_plan()
        config = _make_tenant_config()

        captured_inputs = {}
        pipeline = MagicMock()

        async def _capturing_run(inputs=None, context=None):
            captured_inputs["value"] = inputs
            return _make_pipeline_result()

        pipeline.run = _capturing_run

        with (
            patch("firefly_dworkers.plans.plan_registry") as mock_pr,
            patch("firefly_dworkers.tenants.registry.tenant_registry") as mock_tr,
            patch("firefly_dworkers.plans.builder.PlanBuilder") as mock_pb_cls,
        ):
            mock_pr.get.return_value = plan
            mock_tr.get.return_value = config
            mock_pb_cls.return_value.build.return_value = pipeline

            resp = client.post(
                "/api/plans/execute/sync",
                json={"plan_name": "test-plan", "tenant_id": "test-tenant", "inputs": {"topic": "AI"}},
            )

        assert resp.status_code == 200
        assert captured_inputs["value"] == {"topic": "AI"}
