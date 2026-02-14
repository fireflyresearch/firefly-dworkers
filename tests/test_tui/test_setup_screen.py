"""Tests for the setup wizard screen."""

from __future__ import annotations

from firefly_dworkers_cli.config import ConfigManager
from firefly_dworkers_cli.tui.screens.setup import (
    SetupScreen,
    _PROVIDER_MODELS,
)


class TestSetupScreen:
    def test_instantiates(self):
        screen = SetupScreen()
        assert screen._selected_model == ""
        assert screen._manual_api_key == ""

    def test_instantiates_with_config_manager(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        screen = SetupScreen(config_manager=mgr)
        assert screen._config_mgr is mgr

    def test_detect_provider_from_key_openai(self):
        assert SetupScreen._detect_provider_from_key("sk-abc123") == "openai"

    def test_detect_provider_from_key_anthropic(self):
        assert SetupScreen._detect_provider_from_key("ant-abc123") == "anthropic"
        assert SetupScreen._detect_provider_from_key("sk-ant-abc123") == "anthropic"

    def test_detect_provider_from_key_groq(self):
        assert SetupScreen._detect_provider_from_key("gsk_abc123") == "groq"

    def test_detect_provider_from_key_unknown(self):
        assert SetupScreen._detect_provider_from_key("unknown-key") is None


class TestProviderModels:
    def test_openai_models_exist(self):
        assert "openai" in _PROVIDER_MODELS
        assert len(_PROVIDER_MODELS["openai"]) > 0

    def test_anthropic_models_exist(self):
        assert "anthropic" in _PROVIDER_MODELS
        assert len(_PROVIDER_MODELS["anthropic"]) > 0

    def test_model_tuples_have_id_and_label(self):
        for provider, models in _PROVIDER_MODELS.items():
            for model_id, label in models:
                assert ":" in model_id, f"{model_id} should have provider:model format"
                assert len(label) > 0, f"Model {model_id} should have a label"
