"""Document chunk model and knowledge repository.

Supports pluggable backends via the :class:`KnowledgeBackend` protocol.
The default backend wraps :class:`MemoryManager` for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from fireflyframework_genai.memory.manager import MemoryManager
from pydantic import BaseModel, Field

from firefly_dworkers.knowledge.backends import InMemoryKnowledgeBackend, KnowledgeBackend


class DocumentChunk(BaseModel):
    """A chunk of indexed document content."""

    chunk_id: str
    source: str  # e.g. "sharepoint://doc/123" or "upload://report.pdf"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeRepository:
    """High-level API for document knowledge.

    Accepts either a :class:`KnowledgeBackend` (new) or a bare
    :class:`MemoryManager` (backward-compatible).  When ``memory`` is
    provided without ``backend``, an :class:`InMemoryKnowledgeBackend`
    adapter is created automatically.

    Each :class:`DocumentChunk` is stored under the key ``doc:<chunk_id>``.
    Search is performed via simple case-insensitive substring matching (MVP).
    """

    _DOC_PREFIX = "doc:"

    def __init__(
        self,
        *,
        backend: KnowledgeBackend | None = None,
        memory: MemoryManager | None = None,
        scope_id: str = "knowledge",
    ) -> None:
        if backend is not None:
            self._backend = backend
        else:
            self._backend = InMemoryKnowledgeBackend(memory=memory, scope_id=scope_id)

    # -- CRUD --------------------------------------------------------------

    def index(self, chunk: DocumentChunk) -> None:
        """Store a document chunk in working memory."""
        self._backend.set_fact(f"{self._DOC_PREFIX}{chunk.chunk_id}", chunk.model_dump())

    def get(self, chunk_id: str) -> DocumentChunk | None:
        """Retrieve a specific chunk by ID."""
        data = self._backend.get_fact(f"{self._DOC_PREFIX}{chunk_id}")
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
        for key, value in self._backend.iter_items():
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
        for key, value in self._backend.iter_items():
            if not key.startswith(self._DOC_PREFIX):
                continue
            chunk = DocumentChunk.model_validate(value)
            sources.add(chunk.source)
        return sorted(sources)

    def clear(self) -> None:
        """Clear all indexed knowledge."""
        self._backend.clear_all()

    @property
    def memory(self) -> MemoryManager:
        """The underlying :class:`MemoryManager` (backward compatibility).

        Raises :class:`AttributeError` if the backend is not memory-based.
        """
        if isinstance(self._backend, InMemoryKnowledgeBackend):
            return self._backend.memory
        raise AttributeError("Backend does not expose a MemoryManager")
