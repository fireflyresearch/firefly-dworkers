"""FIFO question queue for coordinating agent questions during parallel plan execution.

When multiple agents run concurrently and one asks a question, only that agent
pauses. The QuestionQueue tracks pending questions and coordinates focus so the
user answers them in FIFO order.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field


@dataclass
class QuestionEntry:
    """A single queued question from an agent."""

    id: str
    role: str
    question: str
    options: list[str]
    answered: asyncio.Event = field(default_factory=asyncio.Event)
    answer_text: str | None = None

    async def wait(self) -> str:
        """Block until the question is answered. Returns the answer text."""
        await self.answered.wait()
        return self.answer_text or ""


class QuestionQueue:
    """FIFO queue coordinating questions from parallel agents."""

    def __init__(self) -> None:
        self._entries: list[QuestionEntry] = []

    def enqueue(self, role: str, question: str, options: list[str]) -> QuestionEntry:
        """Add a question to the queue. Returns a QuestionEntry the caller can await."""
        entry = QuestionEntry(
            id=uuid.uuid4().hex[:8],
            role=role,
            question=question,
            options=options,
        )
        self._entries.append(entry)
        return entry

    def answer(self, entry_id: str, answer_text: str) -> None:
        """Answer a specific question by its ID."""
        for entry in self._entries:
            if entry.id == entry_id:
                entry.answer_text = answer_text
                entry.answered.set()
                return

    def next_unanswered(self) -> QuestionEntry | None:
        """Return the first unanswered question (FIFO), or None."""
        for entry in self._entries:
            if not entry.answered.is_set():
                return entry
        return None

    @property
    def pending_count(self) -> int:
        """Number of unanswered questions."""
        return sum(1 for e in self._entries if not e.answered.is_set())

    def clear(self) -> None:
        """Remove all entries."""
        self._entries.clear()
