"""Document indexer -- splits raw text into chunks and indexes them."""

from __future__ import annotations

from typing import Any

from firefly_dworkers.knowledge.repository import DocumentChunk, KnowledgeRepository


class DocumentIndexer:
    """Splits raw text content into overlapping chunks and indexes them.

    Parameters:
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of characters that overlap between
            consecutive chunks, providing context continuity.
    """

    def __init__(
        self,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def index_text(
        self,
        source: str,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
        repository: KnowledgeRepository,
    ) -> list[str]:
        """Split *text* into chunks and index them.  Returns chunk IDs."""
        chunks = self._split_text(text)
        chunk_ids: list[str] = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{source}:{i}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                source=source,
                content=chunk_text,
                metadata=metadata or {},
            )
            repository.index(chunk)
            chunk_ids.append(chunk_id)
        return chunk_ids

    def _split_text(self, text: str) -> list[str]:
        """Split *text* into overlapping chunks.

        If the text fits within a single chunk, a one-element list is
        returned.  Empty text produces ``[""]``.
        """
        if len(text) <= self._chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self._chunk_size
            chunks.append(text[start:end])
            start = end - self._chunk_overlap
        return chunks
