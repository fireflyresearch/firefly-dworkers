"""Tests for guard middleware wiring in BaseWorker.

Covers GuardsConfig defaults / parsing, _build_guard_middleware behaviour,
and integration with concrete workers.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from pydantic_ai.models.test import TestModel

from firefly_dworkers.tenants.config import (
    GuardsConfig,
    SecurityConfig,
    TenantConfig,
    WorkerConfig,
)
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.analyst import AnalystWorker
from firefly_dworkers.workers.base import BaseWorker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    guards: GuardsConfig | None = None,
    autonomy: str = "semi_supervised",
) -> TenantConfig:
    """Build a TenantConfig for testing with optional guard overrides."""
    security = SecurityConfig(guards=guards) if guards else SecurityConfig()
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
    )


def _make_worker(
    *,
    guards: GuardsConfig | None = None,
    **kwargs: Any,
) -> BaseWorker:
    """Shortcut: create a BaseWorker with a TestModel."""
    config = _make_config(guards=guards)
    return BaseWorker(
        "guard-test-worker",
        role=WorkerRole.ANALYST,
        tenant_config=config,
        model=TestModel(),
        auto_register=False,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# GuardsConfig model tests
# ---------------------------------------------------------------------------


class TestGuardsConfigDefaults:
    """Verify GuardsConfig defaults are sensible."""

    def test_guards_config_defaults(self) -> None:
        cfg = GuardsConfig()
        assert cfg.prompt_guard_enabled is True
        assert cfg.output_guard_enabled is True
        assert cfg.sanitise_prompts is True
        assert cfg.sanitise_outputs is True
        assert cfg.output_block_categories == ["secrets", "pii"]
        assert cfg.custom_prompt_patterns == []
        assert cfg.custom_output_patterns == {}
        assert cfg.custom_deny_patterns == []
        assert cfg.max_input_length == 0
        assert cfg.max_output_length == 0

    def test_guards_config_from_dict(self) -> None:
        """Verify GuardsConfig parses from a YAML-like dict."""
        data = {
            "prompt_guard_enabled": False,
            "output_guard_enabled": True,
            "sanitise_prompts": False,
            "sanitise_outputs": True,
            "output_block_categories": ["secrets"],
            "custom_prompt_patterns": [r"ignore previous"],
            "custom_output_patterns": {"ssn": r"\d{3}-\d{2}-\d{4}"},
            "custom_deny_patterns": ["BLOCKED"],
            "max_input_length": 5000,
            "max_output_length": 10000,
        }
        cfg = GuardsConfig(**data)
        assert cfg.prompt_guard_enabled is False
        assert cfg.output_block_categories == ["secrets"]
        assert cfg.custom_prompt_patterns == [r"ignore previous"]
        assert cfg.custom_output_patterns == {"ssn": r"\d{3}-\d{2}-\d{4}"}
        assert cfg.custom_deny_patterns == ["BLOCKED"]
        assert cfg.max_input_length == 5000
        assert cfg.max_output_length == 10000


class TestSecurityConfigGuards:
    """Verify SecurityConfig includes guards field."""

    def test_security_config_has_guards(self) -> None:
        sec = SecurityConfig()
        assert isinstance(sec.guards, GuardsConfig)

    def test_security_config_custom_guards(self) -> None:
        sec = SecurityConfig(guards=GuardsConfig(prompt_guard_enabled=False))
        assert sec.guards.prompt_guard_enabled is False


# ---------------------------------------------------------------------------
# _build_guard_middleware tests
# ---------------------------------------------------------------------------


class TestBuildGuardMiddleware:
    """Test the static _build_guard_middleware method."""

    def test_default_config_enables_guards(self) -> None:
        """Default TenantConfig should produce both guard middleware."""
        config = _make_config()
        middleware = BaseWorker._build_guard_middleware(config)
        assert len(middleware) == 2

        from fireflyframework_genai.agents.builtin_middleware import (
            OutputGuardMiddleware,
            PromptGuardMiddleware,
        )

        assert isinstance(middleware[0], PromptGuardMiddleware)
        assert isinstance(middleware[1], OutputGuardMiddleware)

    def test_prompt_guard_disabled(self) -> None:
        """No PromptGuardMiddleware when prompt_guard_enabled=False."""
        guards = GuardsConfig(prompt_guard_enabled=False)
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)

        from fireflyframework_genai.agents.builtin_middleware import (
            OutputGuardMiddleware,
            PromptGuardMiddleware,
        )

        assert len(middleware) == 1
        assert isinstance(middleware[0], OutputGuardMiddleware)
        assert not any(isinstance(m, PromptGuardMiddleware) for m in middleware)

    def test_output_guard_disabled(self) -> None:
        """No OutputGuardMiddleware when output_guard_enabled=False."""
        guards = GuardsConfig(output_guard_enabled=False)
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)

        from fireflyframework_genai.agents.builtin_middleware import (
            OutputGuardMiddleware,
            PromptGuardMiddleware,
        )

        assert len(middleware) == 1
        assert isinstance(middleware[0], PromptGuardMiddleware)
        assert not any(isinstance(m, OutputGuardMiddleware) for m in middleware)

    def test_both_guards_disabled(self) -> None:
        """Empty middleware list when both guards disabled."""
        guards = GuardsConfig(
            prompt_guard_enabled=False,
            output_guard_enabled=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)
        assert middleware == []

    def test_custom_prompt_patterns(self) -> None:
        """Custom patterns are forwarded to PromptGuard."""
        guards = GuardsConfig(
            custom_prompt_patterns=[r"ignore all", r"disregard"],
            output_guard_enabled=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)
        assert len(middleware) == 1

        # The underlying guard should have our custom patterns in _raw_patterns
        prompt_mw = middleware[0]
        assert hasattr(prompt_mw, "_guard")
        assert r"ignore all" in prompt_mw._guard._raw_patterns
        assert r"disregard" in prompt_mw._guard._raw_patterns

    def test_custom_output_patterns(self) -> None:
        """Custom output patterns are forwarded to OutputGuard."""
        guards = GuardsConfig(
            custom_output_patterns={"ssn": r"\d{3}-\d{2}-\d{4}"},
            prompt_guard_enabled=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)
        assert len(middleware) == 1

        output_mw = middleware[0]
        assert hasattr(output_mw, "_guard")
        # custom_patterns appear in _groups["custom"]
        assert "custom" in output_mw._guard._groups
        assert "ssn" in output_mw._guard._groups["custom"]

    def test_custom_deny_patterns(self) -> None:
        """Deny patterns are forwarded to OutputGuard."""
        guards = GuardsConfig(
            custom_deny_patterns=["FORBIDDEN"],
            prompt_guard_enabled=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)
        assert len(middleware) == 1

        output_mw = middleware[0]
        assert hasattr(output_mw, "_guard")
        # deny patterns appear in _groups["deny"]
        assert "deny" in output_mw._guard._groups
        assert any("FORBIDDEN" in str(p.pattern) for p in output_mw._guard._groups["deny"].values())

    def test_sanitise_mode(self) -> None:
        """Sanitise flags propagate correctly."""
        guards = GuardsConfig(
            sanitise_prompts=True,
            sanitise_outputs=True,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)

        prompt_mw, output_mw = middleware[0], middleware[1]
        assert prompt_mw._sanitise is True
        assert output_mw._sanitise is True

    def test_reject_mode(self) -> None:
        """When sanitise=False, middleware is configured to raise errors."""
        guards = GuardsConfig(
            sanitise_prompts=False,
            sanitise_outputs=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)

        prompt_mw, output_mw = middleware[0], middleware[1]
        assert prompt_mw._sanitise is False
        assert output_mw._sanitise is False

    def test_block_categories(self) -> None:
        """Only specified categories trigger blocking."""
        guards = GuardsConfig(
            output_block_categories=["secrets"],
            prompt_guard_enabled=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)

        output_mw = middleware[0]
        assert output_mw._block_categories == ["secrets"]

    def test_max_input_length(self) -> None:
        """max_input_length is passed to PromptGuard."""
        guards = GuardsConfig(
            max_input_length=4096,
            output_guard_enabled=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)
        assert len(middleware) == 1

        prompt_mw = middleware[0]
        assert prompt_mw._guard._max_length == 4096

    def test_max_output_length(self) -> None:
        """max_output_length is passed to OutputGuard."""
        guards = GuardsConfig(
            max_output_length=8192,
            prompt_guard_enabled=False,
        )
        config = _make_config(guards=guards)
        middleware = BaseWorker._build_guard_middleware(config)
        assert len(middleware) == 1

        output_mw = middleware[0]
        assert output_mw._guard._max_length == 8192

    def test_framework_import_fallback(self) -> None:
        """Graceful fallback when framework guard modules are not available."""
        config = _make_config()
        with patch.dict(
            "sys.modules",
            {
                "fireflyframework_genai.agents.builtin_middleware": None,
                "fireflyframework_genai.security.prompt_guard": None,
                "fireflyframework_genai.security.output_guard": None,
            },
        ):
            middleware = BaseWorker._build_guard_middleware(config)
        assert middleware == []


# ---------------------------------------------------------------------------
# Integration with BaseWorker.__init__
# ---------------------------------------------------------------------------


def _get_middlewares(worker: BaseWorker) -> list[Any]:
    """Extract the middleware list from a worker's MiddlewareChain."""
    return worker._middleware._middlewares


class TestWorkerGuardIntegration:
    """Test that guard middleware is properly wired into workers."""

    def test_user_middleware_preserved(self) -> None:
        """User-supplied middleware is not lost when guards are added."""
        fake_mw = MagicMock()
        worker = _make_worker(middleware=[fake_mw])

        middlewares = _get_middlewares(worker)
        assert fake_mw in middlewares
        # 2 default (logging, observability) + 2 guards + 1 user
        assert len(middlewares) >= 3

    def test_guard_middleware_order(self) -> None:
        """Guard middleware comes before user middleware."""
        from fireflyframework_genai.agents.builtin_middleware import (
            OutputGuardMiddleware,
            PromptGuardMiddleware,
        )

        fake_mw = MagicMock()
        worker = _make_worker(middleware=[fake_mw])

        middlewares = _get_middlewares(worker)
        # Find positions
        guard_indices = []
        user_index = None
        for i, mw in enumerate(middlewares):
            if isinstance(mw, (PromptGuardMiddleware, OutputGuardMiddleware)):
                guard_indices.append(i)
            if mw is fake_mw:
                user_index = i

        assert guard_indices, "Should have guard middleware"
        assert user_index is not None, "Should have user middleware"
        assert all(
            gi < user_index for gi in guard_indices
        ), "Guards should come before user middleware"

    def test_worker_has_guard_middleware(self) -> None:
        """Integration test: AnalystWorker gets guard middleware by default."""
        from fireflyframework_genai.agents.builtin_middleware import (
            OutputGuardMiddleware,
            PromptGuardMiddleware,
        )

        config = _make_config()
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)

        middlewares = _get_middlewares(worker)
        has_prompt = any(isinstance(m, PromptGuardMiddleware) for m in middlewares)
        has_output = any(isinstance(m, OutputGuardMiddleware) for m in middlewares)
        assert has_prompt, "AnalystWorker should have PromptGuardMiddleware"
        assert has_output, "AnalystWorker should have OutputGuardMiddleware"

    def test_no_guard_middleware_when_disabled(self) -> None:
        """When both guards disabled, worker has no guard middleware."""
        from fireflyframework_genai.agents.builtin_middleware import (
            OutputGuardMiddleware,
            PromptGuardMiddleware,
        )

        guards = GuardsConfig(
            prompt_guard_enabled=False,
            output_guard_enabled=False,
        )
        worker = _make_worker(guards=guards)

        middlewares = _get_middlewares(worker)
        has_prompt = any(isinstance(m, PromptGuardMiddleware) for m in middlewares)
        has_output = any(isinstance(m, OutputGuardMiddleware) for m in middlewares)
        assert not has_prompt
        assert not has_output
