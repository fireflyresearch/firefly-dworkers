"""Knowledge retriever -- convenience layer over KnowledgeRepository."""

from __future__ import annotations

from firefly_dworkers.knowledge.repository import DocumentChunk, KnowledgeRepository


class KnowledgeRetriever:
    """Searches a :class:`KnowledgeRepository` and returns document chunks.

    Provides convenience methods for common retrieval patterns such as
    source filtering and prompt-ready context formatting.
    """

    def __init__(self, repository: KnowledgeRepository) -> None:
        self._repository = repository

    def retrieve(self, query: str, *, max_results: int = 5) -> list[DocumentChunk]:
        """Retrieve relevant document chunks for a query."""
        return self._repository.search(query, max_results=max_results)

    def retrieve_by_source(self, source: str) -> list[DocumentChunk]:
        """Retrieve all chunks from a specific source."""
        results: list[DocumentChunk] = []
        for key, value in self._repository.memory.working.items():
            if not key.startswith(KnowledgeRepository._DOC_PREFIX):
                continue
            chunk = DocumentChunk.model_validate(value)
            if chunk.source == source:
                results.append(chunk)
        return results

    def get_context_string(self, query: str, *, max_results: int = 5) -> str:
        """Retrieve chunks and format them as a context string for prompt injection.

        Returns an empty string when no chunks match the query.
        """
        chunks = self.retrieve(query, max_results=max_results)
        if not chunks:
            return ""
        parts = [f"### {c.source}\n{c.content}" for c in chunks]
        return "\n\n---\n\n".join(parts)
