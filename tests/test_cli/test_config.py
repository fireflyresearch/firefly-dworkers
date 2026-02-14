"""Tests for the CLI configuration manager."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from firefly_dworkers_cli.config import ConfigManager, _deep_merge


class TestDeepMerge:
    def test_flat_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"models": {"default": "openai:gpt-4o", "research": ""}}
        override = {"models": {"research": "anthropic:claude-sonnet-4-5-20250929"}}
        result = _deep_merge(base, override)
        assert result["models"]["default"] == "openai:gpt-4o"
        assert result["models"]["research"] == "anthropic:claude-sonnet-4-5-20250929"

    def test_override_replaces_non_dict(self):
        base = {"key": "old"}
        override = {"key": {"nested": True}}
        result = _deep_merge(base, override)
        assert result == {"key": {"nested": True}}


class TestConfigManager:
    def test_needs_setup_no_files(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        # Override global path to a non-existent location
        import firefly_dworkers_cli.config as cfg_mod
        original = cfg_mod.GLOBAL_CONFIG_PATH
        cfg_mod.GLOBAL_CONFIG_PATH = tmp_path / "nonexistent" / "config.yaml"
        try:
            assert mgr.needs_setup() is True
        finally:
            cfg_mod.GLOBAL_CONFIG_PATH = original

    def test_needs_setup_with_global_config_and_api_key(self, tmp_path, monkeypatch):
        import firefly_dworkers_cli.config as cfg_mod
        original = cfg_mod.GLOBAL_CONFIG_PATH
        global_config = tmp_path / "global" / "config.yaml"
        global_config.parent.mkdir(parents=True)
        global_config.write_text(
            'id: "default"\nname: "Test"\nmodels:\n  default: "openai:gpt-4o"\n'
        )
        cfg_mod.GLOBAL_CONFIG_PATH = global_config
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
        try:
            mgr = ConfigManager(project_dir=tmp_path)
            assert mgr.needs_setup() is False
        finally:
            cfg_mod.GLOBAL_CONFIG_PATH = original

    def test_load_global_config(self, tmp_path, monkeypatch):
        import firefly_dworkers_cli.config as cfg_mod
        original = cfg_mod.GLOBAL_CONFIG_PATH
        global_config = tmp_path / "global" / "config.yaml"
        global_config.parent.mkdir(parents=True)
        global_config.write_text(
            'id: "test-tenant"\nname: "Test Org"\n'
            'models:\n  default: "openai:gpt-4o"\n'
        )
        cfg_mod.GLOBAL_CONFIG_PATH = global_config
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        try:
            mgr = ConfigManager(project_dir=tmp_path)
            config = mgr.load()
            assert config.id == "test-tenant"
            assert config.name == "Test Org"
            assert config.models.default == "openai:gpt-4o"
        finally:
            cfg_mod.GLOBAL_CONFIG_PATH = original
            # Clean up tenant registry
            from firefly_dworkers.tenants.registry import tenant_registry
            tenant_registry.unregister("test-tenant")

    def test_project_overrides_global(self, tmp_path, monkeypatch):
        import firefly_dworkers_cli.config as cfg_mod
        original = cfg_mod.GLOBAL_CONFIG_PATH

        # Global config
        global_config = tmp_path / "global" / "config.yaml"
        global_config.parent.mkdir(parents=True)
        global_config.write_text(
            'id: "default"\nname: "Global"\n'
            'models:\n  default: "openai:gpt-4o"\n  research: ""\n'
        )

        # Project config
        project_config = tmp_path / ".dworkers" / "config.yaml"
        project_config.parent.mkdir(parents=True)
        project_config.write_text(
            'name: "Project Alpha"\n'
            'models:\n  research: "anthropic:claude-sonnet-4-5-20250929"\n'
        )

        cfg_mod.GLOBAL_CONFIG_PATH = global_config
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        try:
            mgr = ConfigManager(project_dir=tmp_path)
            config = mgr.load()
            assert config.name == "Project Alpha"
            assert config.models.default == "openai:gpt-4o"  # from global
            assert config.models.research == "anthropic:claude-sonnet-4-5-20250929"  # from project
        finally:
            cfg_mod.GLOBAL_CONFIG_PATH = original
            from firefly_dworkers.tenants.registry import tenant_registry
            tenant_registry.unregister("default")

    def test_save_global(self, tmp_path):
        import firefly_dworkers_cli.config as cfg_mod
        original_dir = cfg_mod.GLOBAL_DIR
        original_path = cfg_mod.GLOBAL_CONFIG_PATH
        cfg_mod.GLOBAL_DIR = tmp_path / "global"
        cfg_mod.GLOBAL_CONFIG_PATH = cfg_mod.GLOBAL_DIR / "config.yaml"
        try:
            mgr = ConfigManager(project_dir=tmp_path)
            data = mgr.build_default_config(model="anthropic:claude-sonnet-4-5-20250929")
            path = mgr.save_global(data)
            assert path.exists()
            content = path.read_text()
            assert "anthropic:claude-sonnet-4-5-20250929" in content
        finally:
            cfg_mod.GLOBAL_DIR = original_dir
            cfg_mod.GLOBAL_CONFIG_PATH = original_path

    def test_save_project(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        data = {"models": {"default": "openai:gpt-4o-mini"}}
        path = mgr.save_project(data)
        assert path.exists()
        content = path.read_text()
        assert "gpt-4o-mini" in content

    def test_detect_api_keys(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-456")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        mgr = ConfigManager()
        keys = mgr.detect_api_keys()
        assert "openai" in keys
        assert "anthropic" in keys
        assert "google" not in keys

    def test_available_providers(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-456")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        mgr = ConfigManager()
        providers = mgr.available_providers()
        assert providers == ["anthropic", "openai"]

    def test_model_provider(self):
        mgr = ConfigManager()
        assert mgr.model_provider("openai:gpt-4o") == "openai"
        assert mgr.model_provider("anthropic:claude-sonnet-4-5-20250929") == "anthropic"
        assert mgr.model_provider("gpt-4o") == "openai"  # default

    def test_build_default_config(self):
        mgr = ConfigManager()
        data = mgr.build_default_config(
            model="anthropic:claude-sonnet-4-5-20250929",
            tenant_id="my-org",
            tenant_name="My Organization",
        )
        assert data["id"] == "my-org"
        assert data["name"] == "My Organization"
        assert data["models"]["default"] == "anthropic:claude-sonnet-4-5-20250929"
        assert data["workers"]["analyst"]["enabled"] is True

    def test_env_vars_populate_connectors(self, tmp_path, monkeypatch):
        import firefly_dworkers_cli.config as cfg_mod
        original = cfg_mod.GLOBAL_CONFIG_PATH
        global_config = tmp_path / "global" / "config.yaml"
        global_config.parent.mkdir(parents=True)
        global_config.write_text(
            'id: "default"\nname: "Test"\n'
            'models:\n  default: "openai:gpt-4o"\n'
            'connectors:\n  slack:\n    enabled: true\n'
        )
        cfg_mod.GLOBAL_CONFIG_PATH = global_config
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-my-bot-token")
        try:
            mgr = ConfigManager(project_dir=tmp_path)
            config = mgr.load()
            assert config.connectors.slack.bot_token == "xoxb-my-bot-token"
        finally:
            cfg_mod.GLOBAL_CONFIG_PATH = original
            from firefly_dworkers.tenants.registry import tenant_registry
            tenant_registry.unregister("default")

    def test_load_registers_in_tenant_registry(self, tmp_path, monkeypatch):
        import firefly_dworkers_cli.config as cfg_mod
        original = cfg_mod.GLOBAL_CONFIG_PATH
        global_config = tmp_path / "global" / "config.yaml"
        global_config.parent.mkdir(parents=True)
        global_config.write_text(
            'id: "registry-test"\nname: "Registry Test"\n'
            'models:\n  default: "openai:gpt-4o"\n'
        )
        cfg_mod.GLOBAL_CONFIG_PATH = global_config
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        try:
            mgr = ConfigManager(project_dir=tmp_path)
            mgr.load()
            from firefly_dworkers.tenants.registry import tenant_registry
            assert tenant_registry.has("registry-test")
            config = tenant_registry.get("registry-test")
            assert config.name == "Registry Test"
        finally:
            cfg_mod.GLOBAL_CONFIG_PATH = original
            from firefly_dworkers.tenants.registry import tenant_registry
            tenant_registry.unregister("registry-test")

    def test_tenant_wrapper_unwrapped(self, tmp_path, monkeypatch):
        """Config files with a 'tenant:' wrapper should be unwrapped."""
        import firefly_dworkers_cli.config as cfg_mod
        original = cfg_mod.GLOBAL_CONFIG_PATH
        global_config = tmp_path / "global" / "config.yaml"
        global_config.parent.mkdir(parents=True)
        global_config.write_text(
            'tenant:\n  id: "wrapped"\n  name: "Wrapped Config"\n'
            '  models:\n    default: "openai:gpt-4o"\n'
        )
        cfg_mod.GLOBAL_CONFIG_PATH = global_config
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        try:
            mgr = ConfigManager(project_dir=tmp_path)
            config = mgr.load()
            assert config.id == "wrapped"
            assert config.name == "Wrapped Config"
        finally:
            cfg_mod.GLOBAL_CONFIG_PATH = original
            from firefly_dworkers.tenants.registry import tenant_registry
            tenant_registry.unregister("wrapped")
