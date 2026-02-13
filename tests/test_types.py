from __future__ import annotations

from firefly_dworkers.types import AutonomyLevel, WorkerRole


class TestWorkerRole:
    def test_values(self):
        assert WorkerRole.ANALYST == "analyst"
        assert WorkerRole.RESEARCHER == "researcher"
        assert WorkerRole.DATA_ANALYST == "data_analyst"
        assert WorkerRole.MANAGER == "manager"

    def test_str_enum(self):
        assert str(WorkerRole.ANALYST) == "analyst"
        assert f"role={WorkerRole.ANALYST}" == "role=analyst"


class TestAutonomyLevel:
    def test_values(self):
        assert AutonomyLevel.MANUAL == "manual"
        assert AutonomyLevel.SEMI_SUPERVISED == "semi_supervised"
        assert AutonomyLevel.AUTONOMOUS == "autonomous"
