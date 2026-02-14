from __future__ import annotations

import pytest

from firefly_dworkers.autonomy.checkpoint import CheckpointStore
from firefly_dworkers.autonomy.levels import should_checkpoint
from firefly_dworkers.autonomy.reviewer import AutoApproveReviewer, PendingReviewer
from firefly_dworkers.types import AutonomyLevel


class TestShouldCheckpoint:
    def test_manual_always_checkpoints(self):
        assert should_checkpoint(AutonomyLevel.MANUAL, "any_phase") is True

    def test_autonomous_never_checkpoints(self):
        assert should_checkpoint(AutonomyLevel.AUTONOMOUS, "any_phase") is False

    def test_semi_supervised_phase_transition(self):
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "phase_transition") is True

    def test_semi_supervised_deliverable(self):
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "deliverable") is True

    def test_semi_supervised_internal_step(self):
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "internal_step") is False


class TestCheckpointStore:
    def test_store_and_retrieve(self):
        store = CheckpointStore()
        store.submit("cp-1", {"data": "test"})
        assert store.is_pending("cp-1")

    def test_approve(self):
        store = CheckpointStore()
        store.submit("cp-1", {"data": "test"})
        store.approve("cp-1")
        assert not store.is_pending("cp-1")
        assert store.is_approved("cp-1")

    def test_reject(self):
        store = CheckpointStore()
        store.submit("cp-1", {"data": "test"})
        store.reject("cp-1", reason="Not good enough")
        assert store.is_rejected("cp-1")


class TestReviewers:
    @pytest.mark.asyncio
    async def test_auto_approve(self):
        reviewer = AutoApproveReviewer()
        result = await reviewer.on_checkpoint("analyst", "phase_1", {"report": "..."})
        assert result is True

    @pytest.mark.asyncio
    async def test_pending_reviewer(self):
        store = CheckpointStore()
        reviewer = PendingReviewer(store)
        result = await reviewer.on_checkpoint("analyst", "phase_1", {"report": "..."})
        assert result is False
        assert len(store.list_pending()) == 1


class TestNewCheckpointTypes:
    def test_semi_supervised_design_spec_approval(self):
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "design_spec_approval") is True

    def test_semi_supervised_pre_render(self):
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "pre_render") is True

    def test_semi_supervised_intermediate_step_still_false(self):
        assert should_checkpoint(AutonomyLevel.SEMI_SUPERVISED, "intermediate_step") is False

    def test_manual_new_types(self):
        assert should_checkpoint(AutonomyLevel.MANUAL, "design_spec_approval") is True
        assert should_checkpoint(AutonomyLevel.MANUAL, "pre_render") is True

    def test_autonomous_new_types(self):
        assert should_checkpoint(AutonomyLevel.AUTONOMOUS, "design_spec_approval") is False
        assert should_checkpoint(AutonomyLevel.AUTONOMOUS, "pre_render") is False
