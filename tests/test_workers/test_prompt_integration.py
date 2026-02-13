"""Tests that workers use the prompt template system."""

from __future__ import annotations

from pydantic_ai.models.test import TestModel

from firefly_dworkers.prompts import load_prompts
from firefly_dworkers.tenants.config import TenantConfig, WorkerConfig
from firefly_dworkers.workers.analyst import AnalystWorker
from firefly_dworkers.workers.data_analyst import DataAnalystWorker
from firefly_dworkers.workers.manager import ManagerWorker
from firefly_dworkers.workers.researcher import ResearcherWorker


def _make_config(
    *,
    verticals: list[str] | None = None,
    custom_instructions: str = "",
    company_name: str = "TestCo",
) -> TenantConfig:
    worker_settings = {
        "analyst": {"custom_instructions": custom_instructions},
        "researcher": {"custom_instructions": custom_instructions},
        "data_analyst": {"custom_instructions": custom_instructions},
        "manager": {"custom_instructions": custom_instructions},
    }
    return TenantConfig(
        id="test-tenant",
        name="Test Tenant",
        verticals=verticals or [],
        workers=WorkerConfig(**worker_settings),
        branding={"company_name": company_name},
    )


class TestWorkerPromptIntegration:
    """Verify workers delegate to the Jinja2 template system."""

    def test_analyst_uses_template_with_company(self) -> None:
        load_prompts()
        config = _make_config(company_name="Acme Corp")
        worker = AnalystWorker(config, model=TestModel(), auto_register=False)
        assert "Acme Corp" in worker._instructions_text

    def test_researcher_uses_template_with_verticals(self) -> None:
        load_prompts()
        config = _make_config(verticals=["banking"])
        worker = ResearcherWorker(config, model=TestModel(), auto_register=False)
        assert "banking" in worker._instructions_text.lower()

    def test_data_analyst_uses_template_with_custom(self) -> None:
        load_prompts()
        config = _make_config(custom_instructions="Output CSV format.")
        worker = DataAnalystWorker(config, model=TestModel(), auto_register=False)
        assert "Output CSV format." in worker._instructions_text

    def test_manager_uses_template(self) -> None:
        load_prompts()
        config = _make_config()
        worker = ManagerWorker(config, model=TestModel(), auto_register=False)
        assert "project manager" in worker._instructions_text.lower()
