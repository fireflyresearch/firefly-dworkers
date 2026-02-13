"""Tests for the Knowledge Layer: repository, indexer, and retriever."""

from __future__ import annotations

from fireflyframework_genai.memory.manager import MemoryManager
from fireflyframework_genai.memory.store import InMemoryStore

from firefly_dworkers.knowledge.indexer import DocumentIndexer
from firefly_dworkers.knowledge.repository import DocumentChunk, KnowledgeRepository
from firefly_dworkers.knowledge.retriever import KnowledgeRetriever

# ---------------------------------------------------------------------------
# DocumentChunk
# ---------------------------------------------------------------------------


class TestDocumentChunk:
    """Test the DocumentChunk Pydantic model."""

    def test_create_chunk(self) -> None:
        chunk = DocumentChunk(
            chunk_id="abc123",
            source="sharepoint://doc/1",
            content="Some document text",
            metadata={"author": "Alice"},
        )
        assert chunk.chunk_id == "abc123"
        assert chunk.source == "sharepoint://doc/1"
        assert chunk.content == "Some document text"
        assert chunk.metadata == {"author": "Alice"}

    def test_chunk_defaults(self) -> None:
        chunk = DocumentChunk(
            chunk_id="c1",
            source="upload://report.pdf",
            content="Hello world",
        )
        assert chunk.metadata == {}


# ---------------------------------------------------------------------------
# KnowledgeRepository
# ---------------------------------------------------------------------------


class TestKnowledgeRepository:
    """Test the KnowledgeRepository wrapping MemoryManager."""

    def test_index_and_get(self) -> None:
        repo = KnowledgeRepository()
        chunk = DocumentChunk(
            chunk_id="ch1",
            source="upload://a.txt",
            content="Alpha bravo",
        )
        repo.index(chunk)
        result = repo.get("ch1")
        assert result is not None
        assert result.chunk_id == "ch1"
        assert result.content == "Alpha bravo"

    def test_get_missing(self) -> None:
        repo = KnowledgeRepository()
        assert repo.get("nonexistent") is None

    def test_search_by_keyword(self) -> None:
        repo = KnowledgeRepository()
        repo.index(DocumentChunk(chunk_id="s1", source="s", content="The quick brown fox"))
        repo.index(DocumentChunk(chunk_id="s2", source="s", content="Jumped over the lazy dog"))
        repo.index(DocumentChunk(chunk_id="s3", source="s", content="The fox ran away"))

        results = repo.search("fox")
        assert len(results) == 2
        ids = {r.chunk_id for r in results}
        assert ids == {"s1", "s3"}

    def test_search_case_insensitive(self) -> None:
        repo = KnowledgeRepository()
        repo.index(DocumentChunk(chunk_id="ci1", source="s", content="Revenue Growth"))
        results = repo.search("revenue growth")
        assert len(results) == 1
        assert results[0].chunk_id == "ci1"

    def test_search_max_results(self) -> None:
        repo = KnowledgeRepository()
        for i in range(20):
            repo.index(DocumentChunk(chunk_id=f"m{i}", source="s", content=f"match keyword item {i}"))
        results = repo.search("keyword", max_results=5)
        assert len(results) == 5

    def test_search_no_match(self) -> None:
        repo = KnowledgeRepository()
        repo.index(DocumentChunk(chunk_id="nm1", source="s", content="Alpha bravo"))
        results = repo.search("zzznotfound")
        assert results == []

    def test_list_sources(self) -> None:
        repo = KnowledgeRepository()
        repo.index(DocumentChunk(chunk_id="ls1", source="upload://a.txt", content="a"))
        repo.index(DocumentChunk(chunk_id="ls2", source="upload://b.txt", content="b"))
        repo.index(DocumentChunk(chunk_id="ls3", source="upload://a.txt", content="c"))

        sources = repo.list_sources()
        assert sorted(sources) == ["upload://a.txt", "upload://b.txt"]

    def test_clear(self) -> None:
        repo = KnowledgeRepository()
        repo.index(DocumentChunk(chunk_id="cl1", source="s", content="data"))
        assert repo.get("cl1") is not None
        repo.clear()
        assert repo.get("cl1") is None

    def test_custom_memory(self) -> None:
        store = InMemoryStore()
        memory = MemoryManager(store=store, working_scope_id="custom-knowledge")
        repo = KnowledgeRepository(memory=memory)
        repo.index(DocumentChunk(chunk_id="cm1", source="s", content="custom"))
        assert repo.get("cm1") is not None
        assert repo.memory is memory


# ---------------------------------------------------------------------------
# DocumentIndexer
# ---------------------------------------------------------------------------


class TestDocumentIndexer:
    """Test the DocumentIndexer text splitting and indexing."""

    def test_index_short_text(self) -> None:
        """Text shorter than chunk_size produces a single chunk."""
        repo = KnowledgeRepository()
        indexer = DocumentIndexer(chunk_size=1000, chunk_overlap=200)
        ids = indexer.index_text("src://doc", "Short text", repository=repo)
        assert len(ids) == 1
        chunk = repo.get(ids[0])
        assert chunk is not None
        assert chunk.content == "Short text"

    def test_index_long_text(self) -> None:
        """Text longer than chunk_size produces multiple chunks."""
        repo = KnowledgeRepository()
        indexer = DocumentIndexer(chunk_size=50, chunk_overlap=10)
        text = "A" * 120  # 120 chars, chunk_size=50, overlap=10
        ids = indexer.index_text("src://big", text, repository=repo)
        assert len(ids) > 1
        # Verify all chunks are stored
        for cid in ids:
            assert repo.get(cid) is not None

    def test_chunk_overlap(self) -> None:
        """Verify overlapping chunk boundaries."""
        indexer = DocumentIndexer(chunk_size=10, chunk_overlap=3)
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 26 chars
        chunks = indexer._split_text(text)
        # chunk 0: [0:10] = "ABCDEFGHIJ"
        # chunk 1: [7:17] = "HIJKLMNOPQ"
        # chunk 2: [14:24] = "OPQRSTUVWX"
        # chunk 3: [21:31] = "UVWXYZ" (partial)
        assert len(chunks) >= 3
        # Check overlap: end of chunk 0 overlaps with start of chunk 1
        assert chunks[0][-3:] == chunks[1][:3]

    def test_chunk_empty_text(self) -> None:
        """Empty text should produce a single empty chunk."""
        indexer = DocumentIndexer(chunk_size=100, chunk_overlap=20)
        chunks = indexer._split_text("")
        assert chunks == [""]

    def test_returns_chunk_ids(self) -> None:
        """index_text returns deterministic chunk IDs based on source and index."""
        repo = KnowledgeRepository()
        indexer = DocumentIndexer(chunk_size=10, chunk_overlap=2)
        ids = indexer.index_text("doc://test", "Hello world, this is a test string", repository=repo)
        for i, cid in enumerate(ids):
            assert cid == f"doc://test:{i}"

    def test_metadata_forwarded(self) -> None:
        """Metadata provided to index_text is stored on each chunk."""
        repo = KnowledgeRepository()
        indexer = DocumentIndexer(chunk_size=1000)
        meta = {"project": "alpha", "version": 2}
        ids = indexer.index_text("src://m", "Some content", metadata=meta, repository=repo)
        chunk = repo.get(ids[0])
        assert chunk is not None
        assert chunk.metadata == meta


# ---------------------------------------------------------------------------
# KnowledgeRetriever
# ---------------------------------------------------------------------------


class TestKnowledgeRetriever:
    """Test the KnowledgeRetriever convenience layer."""

    def _make_retriever(self) -> tuple[KnowledgeRepository, KnowledgeRetriever]:
        repo = KnowledgeRepository()
        repo.index(DocumentChunk(chunk_id="r1", source="src://a", content="revenue forecast Q3"))
        repo.index(DocumentChunk(chunk_id="r2", source="src://a", content="cost analysis report"))
        repo.index(DocumentChunk(chunk_id="r3", source="src://b", content="revenue growth trends"))
        return repo, KnowledgeRetriever(repo)

    def test_retrieve(self) -> None:
        _repo, retriever = self._make_retriever()
        results = retriever.retrieve("revenue")
        assert len(results) == 2
        ids = {r.chunk_id for r in results}
        assert ids == {"r1", "r3"}

    def test_retrieve_by_source(self) -> None:
        _repo, retriever = self._make_retriever()
        results = retriever.retrieve_by_source("src://a")
        assert len(results) == 2
        ids = {r.chunk_id for r in results}
        assert ids == {"r1", "r2"}

    def test_retrieve_by_source_no_match(self) -> None:
        _repo, retriever = self._make_retriever()
        results = retriever.retrieve_by_source("src://missing")
        assert results == []

    def test_get_context_string(self) -> None:
        _repo, retriever = self._make_retriever()
        ctx = retriever.get_context_string("revenue")
        assert "revenue forecast Q3" in ctx
        assert "revenue growth trends" in ctx
        assert "---" in ctx  # separator

    def test_get_context_string_empty(self) -> None:
        _repo, retriever = self._make_retriever()
        ctx = retriever.get_context_string("zzz_nothing_matches")
        assert ctx == ""
