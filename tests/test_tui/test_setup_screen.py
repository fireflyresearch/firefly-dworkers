"""Tests for the multi-screen setup wizard."""

from __future__ import annotations

from firefly_dworkers_cli.config import ConfigManager, _PROVIDER_ENV_KEYS
from firefly_dworkers_cli.tui.screens.setup import (
    ALL_PROVIDERS,
    SetupWizard,
    ProviderScreen,
    ModelScreen,
    ApiKeyScreen,
    ConfigScreen,
    _AUTONOMY_OPTIONS,
    _MODE_OPTIONS,
    _PROVIDER_MODELS,
    _detect_provider_from_key,
)


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
    def test_has_three_mode_options(self):
        assert len(_MODE_OPTIONS) == 3
        labels = [opt[0] for opt in _MODE_OPTIONS]
        assert "auto" in labels
        assert "local" in labels
        assert "remote" in labels


class TestAutonomyOptions:
    def test_has_three_autonomy_options(self):
        assert len(_AUTONOMY_OPTIONS) == 3
        labels = [opt[0] for opt in _AUTONOMY_OPTIONS]
        assert "manual" in labels
        assert "semi_supervised" in labels
        assert "autonomous" in labels


class TestProviderDetection:
    def test_detect_openai(self):
        assert _detect_provider_from_key("sk-abc123def456") == "openai"

    def test_detect_anthropic(self):
        assert _detect_provider_from_key("ant-abc123def") == "anthropic"
        assert _detect_provider_from_key("sk-ant-abc123") == "anthropic"

    def test_detect_groq(self):
        assert _detect_provider_from_key("gsk_abc123def") == "groq"

    def test_detect_google(self):
        assert _detect_provider_from_key("AIzaSyAbc123def456") == "google"

    def test_detect_mistral(self):
        assert _detect_provider_from_key("mistral-abc123def456") == "mistral"

    def test_unknown_key_accepted(self):
        assert _detect_provider_from_key("some-random-key-format-12345") == "unknown"

    def test_short_key_rejected(self):
        assert _detect_provider_from_key("short") is None


class TestAllProviders:
    def test_all_providers_list(self):
        assert len(ALL_PROVIDERS) == 6
        names = [p[0] for p in ALL_PROVIDERS]
        assert "openai" in names
        assert "anthropic" in names
        assert "google" in names
        assert "mistral" in names
        assert "groq" in names
        assert "other" in names


class TestSetupWizard:
    def test_instantiates(self):
        wizard = SetupWizard()
        assert wizard._selected_provider == ""
        assert wizard._selected_model == ""
        assert wizard._api_key == ""
        assert wizard._selected_mode == "auto"
        assert wizard._selected_autonomy == "semi_supervised"

    def test_instantiates_with_config_manager(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        wizard = SetupWizard(config_manager=mgr)
        assert wizard._config_mgr is mgr


class TestProviderScreen:
    def test_instantiates(self):
        screen = ProviderScreen({})
        assert screen._detected is not None

    def test_instantiates_with_detected(self):
        screen = ProviderScreen({"openai": "sk-test"})
        assert "openai" in screen._detected


class TestModelScreen:
    def test_instantiates_known_provider(self):
        screen = ModelScreen("openai")
        assert screen._provider == "openai"

    def test_instantiates_unknown_provider(self):
        screen = ModelScreen("other")
        assert screen._provider == "other"


class TestApiKeyScreen:
    def test_instantiates(self):
        screen = ApiKeyScreen("anthropic")
        assert screen._provider == "anthropic"


class TestConfigScreen:
    def test_instantiates(self):
        screen = ConfigScreen()
        assert screen._selected_mode == "auto"
        assert screen._selected_autonomy == "semi_supervised"


class TestBuildDefaultConfig:
    def test_includes_mode_and_autonomy(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        config = mgr.build_default_config(mode="local", default_autonomy="manual")
        assert config["mode"] == "local"
        assert config["default_autonomy"] == "manual"

    def test_defaults(self, tmp_path):
        mgr = ConfigManager(project_dir=tmp_path)
        config = mgr.build_default_config()
        assert config["mode"] == "auto"
        assert config["default_autonomy"] == "semi_supervised"
