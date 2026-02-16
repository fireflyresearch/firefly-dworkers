"""Tests for QuestionQueue -- FIFO coordination of agent questions."""

import asyncio

import pytest

from firefly_dworkers_cli.tui.question_queue import QuestionQueue


class TestQuestionQueue:
    @pytest.mark.asyncio
    async def test_enqueue_and_wait(self):
        q = QuestionQueue()
        entry = q.enqueue("analyst", "Pick a strategy", ["A", "B"])
        assert entry.role == "analyst"
        assert not entry.answered.is_set()
        assert q.pending_count == 1

    @pytest.mark.asyncio
    async def test_answer_resolves_event(self):
        q = QuestionQueue()
        entry = q.enqueue("analyst", "Pick?", ["A", "B"])
        q.answer(entry.id, "A")
        assert entry.answered.is_set()
        assert entry.answer_text == "A"
        assert q.pending_count == 0

    @pytest.mark.asyncio
    async def test_fifo_order(self):
        q = QuestionQueue()
        e1 = q.enqueue("analyst", "Q1?", ["A"])
        e2 = q.enqueue("researcher", "Q2?", ["B"])
        assert q.next_unanswered() is e1
        q.answer(e1.id, "A")
        assert q.next_unanswered() is e2

    @pytest.mark.asyncio
    async def test_empty_queue(self):
        q = QuestionQueue()
        assert q.next_unanswered() is None
        assert q.pending_count == 0

    @pytest.mark.asyncio
    async def test_wait_for_answer(self):
        q = QuestionQueue()
        entry = q.enqueue("analyst", "Pick?", ["A", "B"])

        async def answer_later():
            await asyncio.sleep(0.01)
            q.answer(entry.id, "B")

        async with asyncio.TaskGroup() as tg:
            tg.create_task(answer_later())
            tg.create_task(entry.wait())
        assert entry.answer_text == "B"

    @pytest.mark.asyncio
    async def test_clear(self):
        q = QuestionQueue()
        q.enqueue("analyst", "Q?", ["A"])
        q.enqueue("researcher", "Q2?", ["B"])
        assert q.pending_count == 2
        q.clear()
        assert q.pending_count == 0
        assert q.next_unanswered() is None
