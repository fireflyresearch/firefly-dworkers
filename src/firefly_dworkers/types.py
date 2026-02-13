from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class WorkerRole(StrEnum):
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    DATA_ANALYST = "data_analyst"
    MANAGER = "manager"


class AutonomyLevel(StrEnum):
    MANUAL = "manual"
    SEMI_SUPERVISED = "semi_supervised"
    AUTONOMOUS = "autonomous"


@runtime_checkable
class CheckpointHandler(Protocol):
    async def on_checkpoint(self, worker_name: str, phase: str, deliverable: Any) -> bool: ...


TenantId = str
ProjectId = str
PlanName = str
VerticalName = str
ConnectorConfig = dict[str, Any]
