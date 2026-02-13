"""Tests for observability: tracing, metrics, and cost tracking.

Covers ObservabilityConfig model, _build_cost_middleware behaviour,
HTTP trace propagation, and the usage/metrics API endpoints.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from pydantic_ai.models.test import TestModel

from firefly_dworkers.tenants.config import (
    GuardsConfig,
    ObservabilityConfig,
    SecurityConfig,
    TenantConfig,
    WorkerConfig,
)
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.base import BaseWorker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    observability: ObservabilityConfig | None = None,
    guards: GuardsConfig | None = None,
    autonomy: str = "semi_supervised",
) -> TenantConfig:
    """Build a TenantConfig for testing with optional observability overrides."""
    security = SecurityConfig(guards=guards) if guards else SecurityConfig()
    obs = observability or ObservabilityConfig()
    worker_settings = {
        "analyst": {"autonomy": autonomy},
        "researcher": {"autonomy": autonomy},
        "data_analyst": {"autonomy": autonomy},
        "manager": {"autonomy": autonomy},
    }
    return TenantConfig(
        id="test-tenant",
        name="Test Tenant",
        workers=WorkerConfig(**worker_settings),
        security=security,
        observability=obs,
    )


def _make_worker(
    *,
    observability: ObservabilityConfig | None = None,
    guards: GuardsConfig | None = None,
    **kwargs: Any,
) -> BaseWorker:
    """Shortcut: create a BaseWorker with a TestModel."""
    config = _make_config(
        observability=observability,
        guards=GuardsConfig(
            prompt_guard_enabled=False,
            output_guard_enabled=False,
        )
        if guards is None
        else guards,
    )
    return BaseWorker(
        "obs-test-worker",
        role=WorkerRole.ANALYST,
        tenant_config=config,
        model=TestModel(),
        auto_register=False,
        **kwargs,
    )


def _get_middlewares(worker: BaseWorker) -> list[Any]:
    """Extract the middleware list from a worker's MiddlewareChain."""
    return worker._middleware._middlewares


# ---------------------------------------------------------------------------
# ObservabilityConfig model tests
# ---------------------------------------------------------------------------


class TestObservabilityConfig:
    """Test the ObservabilityConfig Pydantic model."""

    def test_defaults(self) -> None:
        cfg = ObservabilityConfig()
        assert cfg.cost_budget_usd == 0.0
        assert cfg.cost_warn_only is True
        assert cfg.per_call_limit_usd == 0.0
        assert cfg.enable_tracing is True
        assert cfg.log_level == "INFO"

    def test_from_dict(self) -> None:
        """Parse from a YAML-like dict."""
        data = {
            "cost_budget_usd": 10.0,
            "cost_warn_only": False,
            "per_call_limit_usd": 0.50,
            "enable_tracing": False,
            "log_level": "DEBUG",
        }
        cfg = ObservabilityConfig(**data)
        assert cfg.cost_budget_usd == 10.0
        assert cfg.cost_warn_only is False
        assert cfg.per_call_limit_usd == 0.50
        assert cfg.enable_tracing is False
        assert cfg.log_level == "DEBUG"

    def test_zero_budget_means_disabled(self) -> None:
        """When budget is 0 and per_call_limit is 0, cost guard is disabled."""
        cfg = ObservabilityConfig()
        assert cfg.cost_budget_usd <= 0
        assert cfg.per_call_limit_usd <= 0

    def test_tenant_config_has_observability(self) -> None:
        """TenantConfig should include observability field."""
        config = TenantConfig(id="t1", name="T1")
        assert isinstance(config.observability, ObservabilityConfig)
        assert config.observability.cost_budget_usd == 0.0

    def test_tenant_config_custom_observability(self) -> None:
        """TenantConfig accepts custom observability settings."""
        obs = ObservabilityConfig(cost_budget_usd=25.0, log_level="WARNING")
        config = TenantConfig(id="t1", name="T1", observability=obs)
        assert config.observability.cost_budget_usd == 25.0
        assert config.observability.log_level == "WARNING"


# ---------------------------------------------------------------------------
# _build_cost_middleware tests
# ---------------------------------------------------------------------------


class TestBuildCostMiddleware:
    """Test the static _build_cost_middleware method."""

    def test_no_middleware_when_budget_zero(self) -> None:
        """Default config (budget=0, per_call=0) yields no cost middleware."""
        config = _make_config()
        middleware = BaseWorker._build_cost_middleware(config)
        assert middleware == []

    def test_middleware_with_budget(self) -> None:
        """Non-zero budget produces CostGuardMiddleware."""
        obs = ObservabilityConfig(cost_budget_usd=5.0)
        config = _make_config(observability=obs)
        middleware = BaseWorker._build_cost_middleware(config)
        assert len(middleware) == 1

        from fireflyframework_genai.agents.builtin_middleware import (
            CostGuardMiddleware,
        )

        assert isinstance(middleware[0], CostGuardMiddleware)

    def test_middleware_with_per_call_limit(self) -> None:
        """Non-zero per_call_limit produces CostGuardMiddleware."""
        obs = ObservabilityConfig(per_call_limit_usd=0.25)
        config = _make_config(observability=obs)
        middleware = BaseWorker._build_cost_middleware(config)
        assert len(middleware) == 1

        from fireflyframework_genai.agents.builtin_middleware import (
            CostGuardMiddleware,
        )

        assert isinstance(middleware[0], CostGuardMiddleware)

    def test_middleware_with_both(self) -> None:
        """Both budget and per_call_limit set: single CostGuardMiddleware."""
        obs = ObservabilityConfig(cost_budget_usd=10.0, per_call_limit_usd=0.50)
        config = _make_config(observability=obs)
        middleware = BaseWorker._build_cost_middleware(config)
        assert len(middleware) == 1

    def test_warn_only_flag(self) -> None:
        """warn_only flag is passed through to CostGuardMiddleware."""
        obs = ObservabilityConfig(cost_budget_usd=5.0, cost_warn_only=True)
        config = _make_config(observability=obs)
        middleware = BaseWorker._build_cost_middleware(config)
        assert len(middleware) == 1
        assert middleware[0]._warn_only is True

    def test_warn_only_false(self) -> None:
        """warn_only=False blocks instead of warning."""
        obs = ObservabilityConfig(cost_budget_usd=5.0, cost_warn_only=False)
        config = _make_config(observability=obs)
        middleware = BaseWorker._build_cost_middleware(config)
        assert len(middleware) == 1
        assert middleware[0]._warn_only is False

    def test_framework_import_fallback(self) -> None:
        """Graceful fallback when CostGuardMiddleware is not available."""
        obs = ObservabilityConfig(cost_budget_usd=5.0)
        config = _make_config(observability=obs)
        with patch.dict(
            "sys.modules",
            {"fireflyframework_genai.agents.builtin_middleware": None},
        ):
            middleware = BaseWorker._build_cost_middleware(config)
        assert middleware == []


# ---------------------------------------------------------------------------
# Worker integration tests
# ---------------------------------------------------------------------------


class TestWorkerCostMiddlewareIntegration:
    """Test cost middleware wired into BaseWorker.__init__."""

    def test_worker_with_budget_has_cost_middleware(self) -> None:
        """Worker created with budget config has CostGuardMiddleware."""
        from fireflyframework_genai.agents.builtin_middleware import (
            CostGuardMiddleware,
        )

        obs = ObservabilityConfig(cost_budget_usd=5.0)
        worker = _make_worker(observability=obs)
        middlewares = _get_middlewares(worker)
        has_cost = any(isinstance(m, CostGuardMiddleware) for m in middlewares)
        assert has_cost, "Worker should have CostGuardMiddleware"

    def test_worker_without_budget_no_cost_middleware(self) -> None:
        """Worker with default config (no budget) has no CostGuardMiddleware."""
        from fireflyframework_genai.agents.builtin_middleware import (
            CostGuardMiddleware,
        )

        worker = _make_worker()
        middlewares = _get_middlewares(worker)
        has_cost = any(isinstance(m, CostGuardMiddleware) for m in middlewares)
        assert not has_cost

    def test_cost_middleware_ordering(self) -> None:
        """Cost middleware comes after guards but before user middleware."""
        from fireflyframework_genai.agents.builtin_middleware import (
            CostGuardMiddleware,
            OutputGuardMiddleware,
            PromptGuardMiddleware,
        )

        obs = ObservabilityConfig(cost_budget_usd=5.0)
        fake_mw = MagicMock()
        worker = _make_worker(
            observability=obs,
            guards=GuardsConfig(),  # Enable guards
            middleware=[fake_mw],
        )

        middlewares = _get_middlewares(worker)
        guard_indices: list[int] = []
        cost_indices: list[int] = []
        user_index: int | None = None

        for i, mw in enumerate(middlewares):
            if isinstance(mw, (PromptGuardMiddleware, OutputGuardMiddleware)):
                guard_indices.append(i)
            elif isinstance(mw, CostGuardMiddleware):
                cost_indices.append(i)
            elif mw is fake_mw:
                user_index = i

        assert guard_indices, "Should have guard middleware"
        assert cost_indices, "Should have cost middleware"
        assert user_index is not None, "Should have user middleware"

        # Guards before cost middleware
        assert all(gi < ci for gi in guard_indices for ci in cost_indices), "Guards should come before cost middleware"
        # Cost middleware before user middleware
        assert all(ci < user_index for ci in cost_indices), "Cost middleware should come before user middleware"

    def test_user_middleware_preserved_with_cost(self) -> None:
        """User middleware is preserved when cost middleware is active."""
        fake_mw = MagicMock()
        obs = ObservabilityConfig(cost_budget_usd=5.0)
        worker = _make_worker(observability=obs, middleware=[fake_mw])
        middlewares = _get_middlewares(worker)
        assert fake_mw in middlewares


# ---------------------------------------------------------------------------
# HTTP trace propagation tests
# ---------------------------------------------------------------------------


class TestConfigureObservability:
    """Test _configure_observability wires trace propagation."""

    def test_trace_propagation_added(self) -> None:
        """Verify add_trace_propagation_middleware is called on the app."""
        from firefly_dworkers_server.app import _configure_observability

        mock_app = MagicMock()
        with patch("fireflyframework_genai.exposure.rest.middleware.add_trace_propagation_middleware") as mock_add:
            _configure_observability(mock_app)
            mock_add.assert_called_once_with(mock_app)

    def test_trace_propagation_import_fallback(self) -> None:
        """Gracefully handles missing framework REST middleware."""
        from firefly_dworkers_server.app import _configure_observability

        mock_app = MagicMock()
        with patch.dict(
            "sys.modules",
            {"fireflyframework_genai.exposure.rest.middleware": None},
        ):
            # Should not raise
            _configure_observability(mock_app)


# ---------------------------------------------------------------------------
# Observability API tests
# ---------------------------------------------------------------------------


class TestObservabilityAPI:
    """Test the /api/observability/* endpoints."""

    def setup_method(self) -> None:
        from fastapi.testclient import TestClient

        from firefly_dworkers_server.app import create_dworkers_app

        self.app = create_dworkers_app()
        self.client = TestClient(self.app)

    def test_get_usage(self) -> None:
        resp = self.client.get("/api/observability/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tokens" in data
        assert "total_cost_usd" in data
        assert "total_requests" in data
        assert "total_latency_ms" in data
        assert "by_agent" in data
        assert "by_model" in data

    def test_get_agent_usage(self) -> None:
        resp = self.client.get("/api/observability/usage/analyst")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tokens" in data
        assert "total_cost_usd" in data

    def test_get_usage_returns_defaults_when_no_data(self) -> None:
        """Without any recorded usage, returns zero values."""
        resp = self.client.get("/api/observability/usage")
        data = resp.json()
        assert data["total_tokens"] >= 0
        assert data["total_cost_usd"] >= 0.0
        assert data["total_requests"] >= 0


# ---------------------------------------------------------------------------
# UsageResponse model tests
# ---------------------------------------------------------------------------


class TestUsageResponse:
    """Test the UsageResponse Pydantic model."""

    def test_default_values(self) -> None:
        from firefly_dworkers_server.api.observability import UsageResponse

        resp = UsageResponse()
        assert resp.total_tokens == 0
        assert resp.total_cost_usd == 0.0
        assert resp.total_requests == 0
        assert resp.total_latency_ms == 0.0
        assert resp.by_agent == {}
        assert resp.by_model == {}

    def test_from_dict(self) -> None:
        from firefly_dworkers_server.api.observability import UsageResponse

        data = {
            "total_tokens": 1500,
            "total_cost_usd": 0.05,
            "total_requests": 3,
            "total_latency_ms": 250.0,
            "by_agent": {"analyst": {"tokens": 1000}},
            "by_model": {"gpt-4o": {"tokens": 1500}},
        }
        resp = UsageResponse(**data)
        assert resp.total_tokens == 1500
        assert resp.total_cost_usd == 0.05
        assert resp.total_requests == 3
        assert resp.by_agent == {"analyst": {"tokens": 1000}}
        assert resp.by_model == {"gpt-4o": {"tokens": 1500}}

    def test_validates_correctly(self) -> None:
        """Ensure extra fields are rejected or model validates types."""
        from firefly_dworkers_server.api.observability import UsageResponse

        resp = UsageResponse(total_tokens=100)
        assert resp.total_tokens == 100
        assert resp.total_cost_usd == 0.0  # default
