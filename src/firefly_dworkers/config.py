from __future__ import annotations

import threading
from typing import Literal

from pydantic_settings import BaseSettings

_lock = threading.Lock()
_instance: DworkersConfig | None = None


class DworkersConfig(BaseSettings):
    model_config = {"env_prefix": "DWORKERS_"}

    default_autonomy: Literal["manual", "semi_supervised", "autonomous"] = "semi_supervised"
    tenant_config_dir: str = "config/tenants"
    max_concurrent_workers: int = 10
    knowledge_backend: Literal["in_memory", "file", "postgres", "mongodb"] = "in_memory"
    default_failure_strategy: Literal["skip_downstream", "fail_pipeline", "ignore"] = "fail_pipeline"


def get_config() -> DworkersConfig:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = DworkersConfig()
    return _instance


def reset_config() -> None:
    global _instance
    with _lock:
        _instance = None
