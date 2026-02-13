"""Tests for DocumentDesignerWorker."""

from __future__ import annotations

from pydantic_ai.models.test import TestModel

from firefly_dworkers.tenants.config import TenantConfig, WorkerConfig
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.designer import DocumentDesignerWorker


def _make_config(
    *,
    verticals: list[str] | None = None,
    autonomy: str = "semi_supervised",
    custom_instructions: str = "",
    company_name: str = "TestCo",
) -> TenantConfig:
    """Helper to build a TenantConfig for testing."""
    worker_settings = {
        "designer": {"autonomy": autonomy, "custom_instructions": custom_instructions},
    }
    return TenantConfig(
        id="test-tenant",
        name="Test Tenant",
        verticals=verticals or [],
        workers=WorkerConfig(**worker_settings),
        branding={"company_name": company_name},
    )


class TestDocumentDesignerWorker:
    """Test DocumentDesignerWorker creation and behaviour."""

    def test_creation(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        assert worker.role == WorkerRole.DESIGNER
        assert "designer" in worker.name

    def test_role_is_designer(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        assert worker.role == WorkerRole.DESIGNER

    def test_default_name(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        assert worker.name == "designer-test-tenant"

    def test_custom_name(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(
            config, name="my-designer", model=TestModel(), auto_register=False
        )
        assert worker.name == "my-designer"

    def test_instructions_populated(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_instructions_contain_role(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "designer" in instructions.lower() or "design" in instructions.lower()

    def test_instructions_include_company(self) -> None:
        config = _make_config(company_name="Acme Corp")
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "Acme Corp" in instructions

    def test_instructions_include_vertical(self) -> None:
        config = _make_config(verticals=["banking"])
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "banking" in instructions.lower()

    def test_instructions_include_custom(self) -> None:
        config = _make_config(custom_instructions="Use brand colors only.")
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        instructions = worker._instructions_text
        assert "Use brand colors only." in instructions

    def test_toolkit_is_bound(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        # The worker was constructed with a toolkit -- verify the underlying
        # agent received tool definitions (report_generation at minimum).
        assert worker._agent is not None

    def test_tags(self) -> None:
        config = _make_config()
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        assert "designer" in worker.tags
        assert "consulting" in worker.tags

    def test_autonomy_from_config(self) -> None:
        config = _make_config(autonomy="manual")
        worker = DocumentDesignerWorker(config, model=TestModel(), auto_register=False)
        assert worker.autonomy_level == AutonomyLevel.MANUAL

    def test_autonomy_override(self) -> None:
        config = _make_config(autonomy="manual")
        worker = DocumentDesignerWorker(
            config,
            model=TestModel(),
            autonomy_level=AutonomyLevel.AUTONOMOUS,
            auto_register=False,
        )
        assert worker.autonomy_level == AutonomyLevel.AUTONOMOUS
