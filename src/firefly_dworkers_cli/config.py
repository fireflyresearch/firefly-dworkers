"""Configuration manager for the dworkers CLI/TUI.

Handles loading, merging, and persisting configuration from two levels:
- **Global**: ``~/.dworkers/config.yaml`` — user-wide defaults
- **Project**: ``.dworkers/config.yaml`` — per-project overrides

The merge strategy is: project config values override global config values
(deep merge at the YAML dict level). The resulting config is registered in
the core ``tenant_registry`` so that ``LocalClient`` and workers can use it.

Environment variables (``OPENAI_API_KEY``, ``ANTHROPIC_API_KEY``, etc.)
are detected and used to auto-populate connector credentials when the
config file doesn't specify them.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from firefly_dworkers.tenants.config import (
    ConnectorsConfig,
    ModelsConfig,
    TenantConfig,
)

logger = logging.getLogger(__name__)

# Directories and file names
GLOBAL_DIR = Path.home() / ".dworkers"
GLOBAL_CONFIG_PATH = GLOBAL_DIR / "config.yaml"
PROJECT_DIR_NAME = ".dworkers"
PROJECT_CONFIG_NAME = "config.yaml"

# Environment variable mappings — env var name → path in config dict
_ENV_VAR_MAP: dict[str, tuple[str, ...]] = {
    "OPENAI_API_KEY": ("_env", "openai_api_key"),
    "ANTHROPIC_API_KEY": ("_env", "anthropic_api_key"),
    "TAVILY_API_KEY": ("connectors", "web_search", "api_key"),
    "SLACK_BOT_TOKEN": ("connectors", "slack", "bot_token"),
    "SLACK_APP_TOKEN": ("connectors", "slack", "app_token"),
    "TEAMS_CLIENT_ID": ("connectors", "teams", "client_id"),
    "TEAMS_CLIENT_SECRET": ("connectors", "teams", "client_secret"),
    "TEAMS_TENANT_ID": ("connectors", "teams", "tenant_id"),
}

# Supported model providers and their env-var key names
_PROVIDER_ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (mutates *base*)."""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _project_config_path(project_dir: Path | None = None) -> Path:
    """Return the project-level config path."""
    root = project_dir or Path.cwd()
    return root / PROJECT_DIR_NAME / PROJECT_CONFIG_NAME


class ConfigManager:
    """Loads, merges, and persists dworkers configuration.

    Usage::

        mgr = ConfigManager()
        if mgr.needs_setup():
            # launch setup wizard
            ...
        else:
            config = mgr.load()
            # config is now registered in tenant_registry
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        self._project_dir = project_dir or Path.cwd()
        self._config: TenantConfig | None = None

    # -- Public API -----------------------------------------------------------

    @property
    def config(self) -> TenantConfig | None:
        """The currently loaded config, or None."""
        return self._config

    @property
    def global_config_path(self) -> Path:
        return GLOBAL_CONFIG_PATH

    @property
    def project_config_path(self) -> Path:
        return _project_config_path(self._project_dir)

    def needs_setup(self) -> bool:
        """Return True if no usable configuration exists.

        A config is "usable" when at least one config file exists AND the
        default model provider has a corresponding API key available (either
        in the config file or as an environment variable).
        """
        has_global = self.global_config_path.exists()
        has_project = self.project_config_path.exists()
        if not has_global and not has_project:
            return True

        # Try to load and check if the model provider has credentials
        try:
            config = self._load_merged_config()
            return not self._has_model_credentials(config)
        except Exception:
            logger.debug("Config load failed during needs_setup", exc_info=True)
            return True

    def load(self) -> TenantConfig:
        """Load, merge, and register the configuration.

        Returns the merged TenantConfig after registering it in
        ``tenant_registry`` as ``"default"``.
        """
        config = self._load_merged_config()
        self._config = config

        # Register in tenant_registry so LocalClient can find it
        from firefly_dworkers.tenants.registry import tenant_registry
        tenant_registry.register(config)
        logger.info(
            "Registered config '%s' (model=%s)",
            config.id,
            config.models.default,
        )
        return config

    def save_global(self, config_data: dict[str, Any]) -> Path:
        """Write configuration to the global config file."""
        GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
        self._write_yaml(self.global_config_path, config_data)
        logger.info("Saved global config to %s", self.global_config_path)
        return self.global_config_path

    def save_project(self, config_data: dict[str, Any]) -> Path:
        """Write configuration to the project config file."""
        project_dir = self._project_dir / PROJECT_DIR_NAME
        project_dir.mkdir(parents=True, exist_ok=True)
        self._write_yaml(self.project_config_path, config_data)
        logger.info("Saved project config to %s", self.project_config_path)
        return self.project_config_path

    def detect_api_keys(self) -> dict[str, str]:
        """Detect available API keys from environment variables.

        Returns a dict of provider name → API key for providers that have
        keys set in the environment.
        """
        found: dict[str, str] = {}
        for provider, env_var in _PROVIDER_ENV_KEYS.items():
            key = os.environ.get(env_var, "")
            if key:
                found[provider] = key
        return found

    def available_providers(self) -> list[str]:
        """Return provider names that have API keys available."""
        return sorted(self.detect_api_keys().keys())

    def model_provider(self, model_string: str) -> str:
        """Extract the provider from a model string like 'openai:gpt-4o'."""
        if ":" in model_string:
            return model_string.split(":", 1)[0]
        return "openai"  # default provider

    def build_default_config(
        self,
        *,
        model: str = "openai:gpt-4o",
        tenant_id: str = "default",
        tenant_name: str = "Default",
    ) -> dict[str, Any]:
        """Build a minimal config dict suitable for saving."""
        return {
            "id": tenant_id,
            "name": tenant_name,
            "models": {
                "default": model,
                "research": "",
                "analysis": "",
            },
            "workers": {
                "analyst": {"enabled": True, "autonomy": "semi_supervised"},
                "researcher": {"enabled": True, "autonomy": "semi_supervised"},
                "data_analyst": {"enabled": True, "autonomy": "semi_supervised"},
                "manager": {"enabled": True, "autonomy": "semi_supervised"},
                "designer": {"enabled": True, "autonomy": "semi_supervised"},
            },
            "connectors": {
                "web_search": {"enabled": False, "provider": "tavily"},
            },
            "security": {
                "allowed_models": ["openai:*", "anthropic:*", "google:*", "mistral:*", "groq:*"],
            },
        }

    # -- Internal helpers -----------------------------------------------------

    def _load_merged_config(self) -> TenantConfig:
        """Load and deep-merge global + project config files."""
        merged: dict[str, Any] = {}

        # Load global config
        if self.global_config_path.exists():
            global_data = self._read_yaml(self.global_config_path)
            if global_data:
                # Unwrap "tenant:" wrapper if present
                if "tenant" in global_data and isinstance(global_data["tenant"], dict):
                    global_data = global_data["tenant"]
                merged = global_data

        # Load and merge project config
        if self.project_config_path.exists():
            project_data = self._read_yaml(self.project_config_path)
            if project_data:
                if "tenant" in project_data and isinstance(project_data["tenant"], dict):
                    project_data = project_data["tenant"]
                _deep_merge(merged, project_data)

        # Ensure required fields
        merged.setdefault("id", "default")
        merged.setdefault("name", "Default")

        # Apply environment variable overrides for connectors
        self._apply_env_vars(merged)

        return TenantConfig.model_validate(merged)

    def _apply_env_vars(self, config_data: dict[str, Any]) -> None:
        """Inject environment variable values into config dict."""
        for env_var, path in _ENV_VAR_MAP.items():
            value = os.environ.get(env_var, "")
            if not value:
                continue
            # Skip _env pseudo-paths (handled by model provider detection)
            if path[0] == "_env":
                continue
            # Set nested value
            d = config_data
            for key in path[:-1]:
                d = d.setdefault(key, {})
            # Only set if not already configured
            if not d.get(path[-1]):
                d[path[-1]] = value

    def _has_model_credentials(self, config: TenantConfig) -> bool:
        """Check if the default model provider has credentials available."""
        provider = self.model_provider(config.models.default)
        env_key = _PROVIDER_ENV_KEYS.get(provider)
        if env_key and os.environ.get(env_key):
            return True
        # Check if we have any provider with keys available
        return bool(self.detect_api_keys())

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any] | None:
        """Read a YAML file, returning None on error."""
        try:
            raw = path.read_text(encoding="utf-8")
            return yaml.safe_load(raw) or {}
        except Exception:
            logger.warning("Failed to read config file: %s", path, exc_info=True)
            return None

    @staticmethod
    def _write_yaml(path: Path, data: dict[str, Any]) -> None:
        """Write a dict to a YAML file."""
        content = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        path.write_text(content, encoding="utf-8")
