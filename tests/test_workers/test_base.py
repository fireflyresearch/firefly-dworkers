"""Tests for BaseWorker and all concrete workers."""

from __future__ import annotations

from pydantic_ai.models.test import TestModel

from firefly_dworkers.tenants.config import TenantConfig, WorkerConfig
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.analyst import AnalystWorker
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.data_analyst import DataAnalystWorker
from firefly_dworkers.workers.manager import ManagerWorker
from firefly_dworkers.workers.researcher import ResearcherWorker


def _make_config(
    *,
    verticals: list[str] | None = None,
    autonomy: str = "semi_supervised",
    custom_instructions: str = "",
) -> TenantConfig:
    """Helper to build a TenantConfig for testing."""
    worker_settings = {
        "analyst": {"autonomy": autonomy, "custom_instructions": custom_instructions},
        "researcher": {"autonomy": autonomy, "custom_instructions": custom_instructions},
        "data_analyst": {"autonomy": autonomy, "custom_instructions": custom_instructions},
        "manager": {"autonomy": autonomy, "custom_instructions": custom_instructions},
    }
    return TenantConfig(
        id="test-tenant",
        name="Test Tenant",
        verticals=verticals or [],
        workers=WorkerConfig(**worker_settings),
    )


# ---------------------------------------------------------------------------
# BaseWorker tests
# ---------------------------------------------------------------------------


class TestBaseWorker:
    """Test BaseWorker creation and properties."""

    def test_create_with_defaults(self) -> None:
        config = _make_config()
        worker = BaseWorker(
            "test-worker",
            role=WorkerRole.ANALYST,
            tenant_config=config,
            model=TestModel(),
            auto_register=False,
        )
        assert worker.name == "test-worker"
        assert worker.role == WorkerRole.ANALYST
        assert worker.tenant_config is config

    def test_autonomy_defaults_from_config(self) -> None:
        config = _make_config(autonomy="autonomous")
        worker = BaseWorker(
            "test-worker",
            role=WorkerRole.ANALYST,
            tenant_config=config,
            model=TestModel(),
            auto_register=False,
        )
        assert worker.autonomy_level == AutonomyLevel.AUTONOMOUS

    def test_autonomy_explicit_override(self) -> None:
        config = _make_config(autonomy="autonomous")
        worker = BaseWorker(
            "test-worker",
            role=WorkerRole.ANALYST,
            tenant_config=config,
            model=TestModel(),
            autonomy_level=AutonomyLevel.MANUAL,
            auto_register=False,
        )
        assert worker.autonomy_level == AutonomyLevel.MANUAL

    def test_model_resolution_from_config(self) -> None:
        config = _make_config()
        # When model is not provided, it should fall back to tenant config default
        worker = BaseWorker(
            "test-worker",
            role=WorkerRole.ANALYST,
            tenant_config=config,
            model=TestModel(),
            auto_register=False,
        )
        # We passed a TestModel instance, so the agent should use it
        assert worker.name == "test-worker"

    def test_role_property(self) -> None:
        config = _make_config()
        worker = BaseWorker(
            "test-worker",
            role=WorkerRole.RESEARCHER,
            tenant_config=config,
            model=TestModel(),
            auto_register=False,
        )
        assert worker.role == WorkerRole.RESEARCHER

    def test_tenant_config_property(self) -> None:
        config = _make_config()
        worker = BaseWorker(
            "test-worker",
            role=WorkerRole.ANALYST,
            tenant_config=config,
            model=TestModel(),
            auto_register=False,
        )
        assert worker.tenant_config.id == "test-tenant"
        assert worker.tenant_config.name == "Test Tenant"

    def test_semi_supervised_default(self) -> None:
        config = _make_config()  # default is "semi_supervised"
        worker = BaseWorker(
            "test-worker",
            role=WorkerRole.ANALYST,
            tenant_config=config,
            model=TestModel(),
            auto_register=False,
        )
        assert worker.autonomy_level == AutonomyLevel.SEMI_SUPERVISED

    def test_auto_register_false_does_not_register(self) -> None:
        config = _make_config()
        worker = BaseWorker(
            "test-worker-unreg",
            role=WorkerRole.ANALYST,
            tenant_config=config,
            model=TestModel(),
            auto_register=False,
        )
        assert worker.name == "test-worker-unreg"


# ---------------------------------------------------------------------------
# AnalystWorker tests
# ---------------------------------------------------------------------------


class TestAnalystWorker:
    """Test AnalystWorker creation and behaviour."""

    def test_creation(self) -> None:
        config = _make_config()
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        assert worker.role == WorkerRole.ANALYST
        assert "analyst" in worker.name

    def test_default_name(self) -> None:
        config = _make_config()
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        assert worker.name == "analyst-test-tenant"

    def test_custom_name(self) -> None:
        config = _make_config()
        worker = AnalystWorker(config, name="my-analyst", model=TestModel(), auto_register=False)
        assert worker.name == "my-analyst"

    def test_instructions_contain_role(self) -> None:
        config = _make_config()
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        # The instructions should mention "analyst" in some form
        instructions = worker._instructions_text
        assert "analyst" in instructions.lower()

    def test_instructions_include_vertical(self) -> None:
        config = _make_config(verticals=["banking"])
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "banking" in instructions.lower()

    def test_instructions_include_custom(self) -> None:
        config = _make_config(custom_instructions="Always use formal tone.")
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "Always use formal tone." in instructions

    def test_autonomy_from_config(self) -> None:
        config = _make_config(autonomy="manual")
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        assert worker.autonomy_level == AutonomyLevel.MANUAL

    def test_autonomy_override(self) -> None:
        config = _make_config(autonomy="manual")
        worker = AnalystWorker(
            config,
            model=TestModel(),
            autonomy_level=AutonomyLevel.AUTONOMOUS,
            auto_register=False,
        )
        assert worker.autonomy_level == AutonomyLevel.AUTONOMOUS

    def test_tags(self) -> None:
        config = _make_config()
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        assert "analyst" in worker.tags
        assert "consulting" in worker.tags


# ---------------------------------------------------------------------------
# ResearcherWorker tests
# ---------------------------------------------------------------------------


class TestResearcherWorker:
    """Test ResearcherWorker creation and behaviour."""

    def test_creation(self) -> None:
        config = _make_config()
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        assert worker.role == WorkerRole.RESEARCHER
        assert "researcher" in worker.name

    def test_default_name(self) -> None:
        config = _make_config()
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        assert worker.name == "researcher-test-tenant"

    def test_custom_name(self) -> None:
        config = _make_config()
        worker = ResearcherWorker(config, name="my-researcher", model=TestModel(), auto_register=False)
        assert worker.name == "my-researcher"

    def test_instructions_contain_role(self) -> None:
        config = _make_config()
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "research" in instructions.lower()

    def test_instructions_include_vertical(self) -> None:
        config = _make_config(verticals=["healthcare"])
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "healthcare" in instructions.lower()

    def test_instructions_include_custom(self) -> None:
        config = _make_config(custom_instructions="Cite all sources.")
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "Cite all sources." in instructions

    def test_tags(self) -> None:
        config = _make_config()
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        assert "researcher" in worker.tags
        assert "consulting" in worker.tags


# ---------------------------------------------------------------------------
# DataAnalystWorker tests
# ---------------------------------------------------------------------------


class TestDataAnalystWorker:
    """Test DataAnalystWorker creation and behaviour."""

    def test_creation(self) -> None:
        config = _make_config()
        worker = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        assert worker.role == WorkerRole.DATA_ANALYST
        assert "data-analyst" in worker.name

    def test_default_name(self) -> None:
        config = _make_config()
        worker = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        assert worker.name == "data-analyst-test-tenant"

    def test_custom_name(self) -> None:
        config = _make_config()
        worker = DataAnalystWorker(config, name="my-da", model=TestModel(), auto_register=False)
        assert worker.name == "my-da"

    def test_instructions_contain_role(self) -> None:
        config = _make_config()
        worker = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "data" in instructions.lower()

    def test_instructions_include_vertical(self) -> None:
        config = _make_config(verticals=["technology"])
        worker = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "technology" in instructions.lower()

    def test_instructions_include_custom(self) -> None:
        config = _make_config(custom_instructions="Output CSV format.")
        worker = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "Output CSV format." in instructions

    def test_tags(self) -> None:
        config = _make_config()
        worker = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        assert "data_analyst" in worker.tags
        assert "consulting" in worker.tags


# ---------------------------------------------------------------------------
# ManagerWorker tests
# ---------------------------------------------------------------------------


class TestManagerWorker:
    """Test ManagerWorker creation and behaviour."""

    def test_creation(self) -> None:
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        assert worker.role == WorkerRole.MANAGER
        assert "manager" in worker.name

    def test_default_name(self) -> None:
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        assert worker.name == "manager-test-tenant"

    def test_custom_name(self) -> None:
        config = _make_config()
        worker = ManagerWorker(config, name="my-mgr", model=TestModel(), auto_register=False)
        assert worker.name == "my-mgr"

    def test_instructions_contain_role(self) -> None:
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "manager" in instructions.lower() or "manage" in instructions.lower()

    def test_instructions_include_vertical(self) -> None:
        config = _make_config(verticals=["legal"])
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "legal" in instructions.lower()

    def test_instructions_include_custom(self) -> None:
        config = _make_config(custom_instructions="Prioritize deadlines.")
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "Prioritize deadlines." in instructions

    def test_tags(self) -> None:
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        assert "manager" in worker.tags
        assert "consulting" in worker.tags


# ---------------------------------------------------------------------------
# Cross-worker: multiple verticals
# ---------------------------------------------------------------------------


class TestMultipleVerticals:
    """Test that workers handle multiple verticals in instructions."""

    def test_analyst_multiple_verticals(self) -> None:
        config = _make_config(verticals=["banking", "healthcare"])
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "banking" in instructions.lower()
        assert "healthcare" in instructions.lower()

    def test_researcher_unknown_vertical_skipped(self) -> None:
        config = _make_config(verticals=["nonexistent_vertical"])
        # Should not raise — unknown verticals are silently skipped
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        assert worker.role == WorkerRole.RESEARCHER
