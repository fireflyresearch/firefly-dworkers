"""Tests for TUICheckpointHandler — bridges core autonomy checkpoints to the TUI."""

from __future__ import annotations

import asyncio

import pytest

from firefly_dworkers_cli.tui.checkpoint_handler import TUICheckpointHandler


class TestTUICheckpointHandler:
    @pytest.mark.asyncio
    async def test_approve_resolves_checkpoint(self):
        handler = TUICheckpointHandler()

        async def worker_task():
            return await handler.on_checkpoint("analyst", "phase1", {"data": "test"})

        task = asyncio.create_task(worker_task())
        await asyncio.sleep(0.01)  # let worker_task run to await

        pending = handler.list_pending()
        assert len(pending) == 1
        cp_id = pending[0].id

        handler.approve(cp_id)
        result = await task
        assert result is True

    @pytest.mark.asyncio
    async def test_reject_resolves_checkpoint(self):
        handler = TUICheckpointHandler()

        async def worker_task():
            return await handler.on_checkpoint("designer", "pre_render", {})

        task = asyncio.create_task(worker_task())
        await asyncio.sleep(0.01)

        pending = handler.list_pending()
        cp_id = pending[0].id

        handler.reject(cp_id, reason="Needs revision")
        result = await task
        assert result is False

    @pytest.mark.asyncio
    async def test_list_pending_empty(self):
        handler = TUICheckpointHandler()
        assert handler.list_pending() == []

    def test_get_nonexistent(self):
        handler = TUICheckpointHandler()
        assert handler.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_approved_checkpoint_status_in_store(self):
        """After approval, the store should reflect APPROVED status."""
        handler = TUICheckpointHandler()

        async def worker_task():
            return await handler.on_checkpoint("analyst", "deliverable", {"report": "v1"})

        task = asyncio.create_task(worker_task())
        await asyncio.sleep(0.01)

        pending = handler.list_pending()
        cp_id = pending[0].id

        handler.approve(cp_id)
        await task

        cp = handler.get(cp_id)
        assert cp is not None
        assert cp.status == "approved"

    @pytest.mark.asyncio
    async def test_rejected_checkpoint_status_in_store(self):
        """After rejection, the store should reflect REJECTED status with reason."""
        handler = TUICheckpointHandler()

        async def worker_task():
            return await handler.on_checkpoint("researcher", "phase_transition", {})

        task = asyncio.create_task(worker_task())
        await asyncio.sleep(0.01)

        pending = handler.list_pending()
        cp_id = pending[0].id

        handler.reject(cp_id, reason="Incomplete data")
        await task

        cp = handler.get(cp_id)
        assert cp is not None
        assert cp.status == "rejected"
        assert cp.rejection_reason == "Incomplete data"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_checkpoints(self):
        """Multiple workers can pause concurrently; each resolves independently."""
        handler = TUICheckpointHandler()

        async def worker_a():
            return await handler.on_checkpoint("analyst", "phase1", {"a": 1})

        async def worker_b():
            return await handler.on_checkpoint("designer", "phase2", {"b": 2})

        task_a = asyncio.create_task(worker_a())
        task_b = asyncio.create_task(worker_b())
        await asyncio.sleep(0.01)

        pending = handler.list_pending()
        assert len(pending) == 2

        # Approve one, reject the other
        ids = {cp.worker_name: cp.id for cp in pending}
        handler.approve(ids["analyst"])
        handler.reject(ids["designer"], reason="wrong colors")

        result_a = await task_a
        result_b = await task_b
        assert result_a is True
        assert result_b is False

    @pytest.mark.asyncio
    async def test_implements_checkpoint_handler_protocol(self):
        """TUICheckpointHandler should satisfy the CheckpointHandler protocol."""
        from firefly_dworkers.types import CheckpointHandler

        handler = TUICheckpointHandler()
        assert isinstance(handler, CheckpointHandler)
