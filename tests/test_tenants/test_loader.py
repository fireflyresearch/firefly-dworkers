from __future__ import annotations

from pathlib import Path

import pytest

from firefly_dworkers.exceptions import TenantError, TenantNotFoundError
from firefly_dworkers.tenants.loader import load_all_tenants, load_tenant_config
from firefly_dworkers.tenants.registry import TenantRegistry

FIXTURES = Path(__file__).parent.parent / "fixtures" / "tenants"


class TestLoadTenantConfig:
    def test_load_yaml(self):
        config = load_tenant_config(FIXTURES / "acme.yaml")
        assert config.id == "acme-consulting"
        assert config.name == "ACME Consulting"
        assert config.models.default == "openai:gpt-4o"
        assert "technology" in config.verticals
        assert config.workers.analyst.autonomy == "semi_supervised"
        assert config.connectors.web_search["provider"] == "tavily"

    def test_missing_file(self):
        with pytest.raises(TenantError, match="not found"):
            load_tenant_config("/nonexistent/path.yaml")

    def test_load_all(self):
        configs = load_all_tenants(FIXTURES)
        assert len(configs) >= 1
        assert any(c.id == "acme-consulting" for c in configs)


class TestTenantRegistry:
    def test_register_and_get(self):
        registry = TenantRegistry()
        config = load_tenant_config(FIXTURES / "acme.yaml")
        registry.register(config)
        assert registry.has("acme-consulting")
        retrieved = registry.get("acme-consulting")
        assert retrieved.name == "ACME Consulting"

    def test_get_missing(self):
        registry = TenantRegistry()
        with pytest.raises(TenantNotFoundError):
            registry.get("nonexistent")

    def test_unregister(self):
        registry = TenantRegistry()
        config = load_tenant_config(FIXTURES / "acme.yaml")
        registry.register(config)
        registry.unregister("acme-consulting")
        assert not registry.has("acme-consulting")

    def test_list_tenants(self):
        registry = TenantRegistry()
        config = load_tenant_config(FIXTURES / "acme.yaml")
        registry.register(config)
        assert "acme-consulting" in registry.list_tenants()
