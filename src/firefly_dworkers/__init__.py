"""firefly-dworkers -- Digital Workers as a Service (DWaaS) platform.

Built on fireflyframework-genai, this package provides AI-powered digital
workers for consulting firms: Analyst, Researcher, Data Analyst, and Manager.

Quick start::

    from firefly_dworkers.config import DworkersConfig, get_config

    config = get_config()
"""

from firefly_dworkers._version import __version__
from firefly_dworkers.config import DworkersConfig, get_config, reset_config
from firefly_dworkers.exceptions import (
    CheckpointError,
    CheckpointRejectedError,
    ConnectorAuthError,
    ConnectorError,
    DworkersError,
    KnowledgeError,
    PlanError,
    PlanNotFoundError,
    TenantError,
    TenantNotFoundError,
    VerticalError,
    VerticalNotFoundError,
    WorkerError,
    WorkerNotFoundError,
)
from firefly_dworkers.types import AutonomyLevel, WorkerRole

__all__ = [
    "__version__",
    "AutonomyLevel",
    "CheckpointError",
    "CheckpointRejectedError",
    "ConnectorAuthError",
    "ConnectorError",
    "DworkersConfig",
    "DworkersError",
    "KnowledgeError",
    "PlanError",
    "PlanNotFoundError",
    "TenantError",
    "TenantNotFoundError",
    "VerticalError",
    "VerticalNotFoundError",
    "WorkerError",
    "WorkerNotFoundError",
    "WorkerRole",
    "get_config",
    "reset_config",
]
