from __future__ import annotations

import pytest

from firefly_dworkers.config import DworkersConfig, get_config, reset_config


class TestDworkersConfig:
    def setup_method(self):
        reset_config()

    def test_default_values(self):
        config = get_config()
        assert config.default_autonomy == "semi_supervised"
        assert config.tenant_config_dir == "config/tenants"
        assert config.max_concurrent_workers == 10

    def test_singleton(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reset(self):
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2

    def test_custom_values(self):
        reset_config()
        config = DworkersConfig(
            default_autonomy="autonomous",
            tenant_config_dir="/custom/path",
            max_concurrent_workers=20,
        )
        assert config.default_autonomy == "autonomous"
        assert config.tenant_config_dir == "/custom/path"

    def test_invalid_autonomy(self):
        with pytest.raises(ValueError):
            DworkersConfig(default_autonomy="invalid")
