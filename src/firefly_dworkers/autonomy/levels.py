from __future__ import annotations

from pydantic import BaseModel

from firefly_dworkers.types import AutonomyLevel

_SEMI_SUPERVISED_CHECKPOINTS = frozenset({"phase_transition", "deliverable", "final_output"})


class AutonomyConfig(BaseModel):
    level: AutonomyLevel = AutonomyLevel.SEMI_SUPERVISED
    checkpoint_types: frozenset[str] = _SEMI_SUPERVISED_CHECKPOINTS


def should_checkpoint(level: AutonomyLevel, checkpoint_type: str) -> bool:
    if level == AutonomyLevel.MANUAL:
        return True
    if level == AutonomyLevel.AUTONOMOUS:
        return False
    return checkpoint_type in _SEMI_SUPERVISED_CHECKPOINTS
