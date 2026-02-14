"""Tests for the setup wizard screen."""

from __future__ import annotations

from pathlib import Path

from firefly_dworkers_cli.config import ConfigManager
from firefly_dworkers_cli.tui.screens.setup import (
    SetupScreen,
    _AUTONOMY_OPTIONS,
    _MODE_OPTIONS,
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
        assert SetupScreen._detect_provider_from_key("sk-abc123def456") == "openai"

    def test_detect_provider_from_key_anthropic(self):
        assert SetupScreen._detect_provider_from_key("ant-abc123") == "anthropic"
        assert SetupScreen._detect_provider_from_key("sk-ant-abc123") == "anthropic"

    def test_detect_provider_from_key_groq(self):
        assert SetupScreen._detect_provider_from_key("gsk_abc123") == "groq"

    def test_detect_provider_from_key_unknown(self):
        assert SetupScreen._detect_provider_from_key("unknown-key") == "unknown"


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


class TestModeOptions:
    def test_setup_screen_has_mode_options(self):
        assert len(_MODE_OPTIONS) == 3
        labels = [opt[0] for opt in _MODE_OPTIONS]
        assert "auto" in labels
        assert "local" in labels
        assert "remote" in labels


class TestAutonomyOptions:
    def test_setup_screen_has_autonomy_options(self):
        assert len(_AUTONOMY_OPTIONS) == 3
        labels = [opt[0] for opt in _AUTONOMY_OPTIONS]
        assert "manual" in labels
        assert "semi_supervised" in labels
        assert "autonomous" in labels


class TestProviderDetectionExtended:
    def test_detect_google_key(self):
        assert SetupScreen._detect_provider_from_key("AIzaSyAbc123def456") == "google"

    def test_detect_mistral_key(self):
        assert SetupScreen._detect_provider_from_key("mistral-abc123def456") == "mistral"

    def test_unknown_key_accepted(self):
        result = SetupScreen._detect_provider_from_key("some-random-key-format-12345")
        assert result == "unknown"

    def test_short_key_rejected(self):
        assert SetupScreen._detect_provider_from_key("short") is None


class TestBuildDefaultConfigModeAutonomy:
    def test_build_default_config_includes_mode_and_autonomy(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        config = mgr.build_default_config(mode="local", default_autonomy="manual")
        assert config["mode"] == "local"
        assert config["default_autonomy"] == "manual"

    def test_build_default_config_mode_and_autonomy_defaults(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        config = mgr.build_default_config()
        assert config["mode"] == "auto"
        assert config["default_autonomy"] == "semi_supervised"
