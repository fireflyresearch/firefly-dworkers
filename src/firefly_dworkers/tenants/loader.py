from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from firefly_dworkers.exceptions import TenantError
from firefly_dworkers.tenants.config import TenantConfig

logger = logging.getLogger(__name__)


def load_tenant_config(path: str | Path) -> TenantConfig:
    path = Path(path)
    if not path.exists():
        raise TenantError(f"Tenant config file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(raw) or {}
    elif path.suffix == ".json":
        data = json.loads(raw)
    else:
        raise TenantError(f"Unsupported config format: {path.suffix}")
    if "tenant" in data and isinstance(data["tenant"], dict):
        data = data["tenant"]
    logger.info("Loaded tenant config '%s' from %s", data.get("id", "?"), path)
    return TenantConfig.model_validate(data)


def load_all_tenants(directory: str | Path) -> list[TenantConfig]:
    directory = Path(directory)
    if not directory.is_dir():
        raise TenantError(f"Tenant config directory not found: {directory}")
    configs = []
    for path in sorted(directory.iterdir()):
        if path.suffix in {".yaml", ".yml", ".json"}:
            configs.append(load_tenant_config(path))
    return configs
