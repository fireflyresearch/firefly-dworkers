"""Document chunk model and knowledge repository backed by MemoryManager."""

from __future__ import annotations

from typing import Any

from fireflyframework_genai.memory.manager import MemoryManager
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A chunk of indexed document content."""

    chunk_id: str
    source: str  # e.g. "sharepoint://doc/123" or "upload://report.pdf"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeRepository:
    """High-level API for document knowledge backed by :class:`MemoryManager`.

    Each :class:`DocumentChunk` is stored as a working-memory fact
    under the key ``doc:<chunk_id>``.  Search is performed via simple
    case-insensitive substring matching (MVP).
    """

    _DOC_PREFIX = "doc:"

    def __init__(
        self,
        *,
        memory: MemoryManager | None = None,
        scope_id: str = "knowledge",
    ) -> None:
        self._memory = memory or MemoryManager(working_scope_id=scope_id)

    # -- CRUD --------------------------------------------------------------

    def index(self, chunk: DocumentChunk) -> None:
        """Store a document chunk in working memory."""
        self._memory.set_fact(f"{self._DOC_PREFIX}{chunk.chunk_id}", chunk.model_dump())

    def get(self, chunk_id: str) -> DocumentChunk | None:
        """Retrieve a specific chunk by ID."""
        data = self._memory.get_fact(f"{self._DOC_PREFIX}{chunk_id}")
        if data is None:
            return None
        return DocumentChunk.model_validate(data)

    # -- Search ------------------------------------------------------------

    def search(self, query: str, *, max_results: int = 10) -> list[DocumentChunk]:
        """Simple case-insensitive keyword search across indexed chunks.

        For MVP this does basic substring matching on content.  Can be
        upgraded to vector similarity search later.
        """
        query_lower = query.lower()
        matches: list[DocumentChunk] = []
        for key, value in self._memory.working.items():
            if not key.startswith(self._DOC_PREFIX):
                continue
            chunk = DocumentChunk.model_validate(value)
            if query_lower in chunk.content.lower():
                matches.append(chunk)
                if len(matches) >= max_results:
                    break
        return matches

    # -- Utilities ---------------------------------------------------------

    def list_sources(self) -> list[str]:
        """Return unique source identifiers of all indexed documents."""
        sources: set[str] = set()
        for key, value in self._memory.working.items():
            if not key.startswith(self._DOC_PREFIX):
                continue
            chunk = DocumentChunk.model_validate(value)
            sources.add(chunk.source)
        return sorted(sources)

    def clear(self) -> None:
        """Clear all indexed knowledge."""
        self._memory.clear_working()

    @property
    def memory(self) -> MemoryManager:
        """The underlying :class:`MemoryManager`."""
        return self._memory
