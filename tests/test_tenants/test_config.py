from __future__ import annotations

from firefly_dworkers.tenants.config import (
    BrandingConfig,
    ConnectorsConfig,
    ModelsConfig,
    SecurityConfig,
    TenantConfig,
    WebSearchConnectorConfig,
    WorkerConfig,
)


class TestTenantConfig:
    def test_minimal_config(self):
        config = TenantConfig(id="test", name="Test Corp")
        assert config.id == "test"
        assert config.name == "Test Corp"
        assert config.verticals == []
        assert config.workers.analyst.enabled is True

    def test_full_config(self):
        config = TenantConfig(
            id="acme",
            name="ACME Consulting",
            models=ModelsConfig(default="openai:gpt-4o", research="anthropic:claude-sonnet-4-5-20250929"),
            verticals=["technology", "banking"],
            workers=WorkerConfig(
                analyst=WorkerConfig.WorkerSettings(
                    enabled=True,
                    autonomy="semi_supervised",
                    custom_instructions="Focus on Agile",
                    max_concurrent_tasks=5,
                )
            ),
            connectors=ConnectorsConfig(
                web_search=WebSearchConnectorConfig(
                    enabled=True, provider="tavily", credential_ref="vault://acme/tavily",
                )
            ),
            branding=BrandingConfig(company_name="ACME Consulting"),
            security=SecurityConfig(allowed_models=["openai:*"], data_residency="eu"),
        )
        assert config.id == "acme"
        assert config.models.research == "anthropic:claude-sonnet-4-5-20250929"
        assert config.workers.analyst.custom_instructions == "Focus on Agile"
        assert config.connectors.web_search.provider == "tavily"
        assert config.security.data_residency == "eu"

    def test_worker_defaults(self):
        config = TenantConfig(id="test", name="Test")
        assert config.workers.analyst.enabled is True
        assert config.workers.analyst.autonomy == "semi_supervised"
        assert config.workers.researcher.enabled is True
        assert config.workers.data_analyst.enabled is True
        assert config.workers.manager.enabled is True
