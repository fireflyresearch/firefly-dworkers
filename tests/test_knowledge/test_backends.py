"""Tests for knowledge backends."""

from __future__ import annotations

from fireflyframework_genai.memory.manager import MemoryManager
from fireflyframework_genai.memory.store import InMemoryStore

from firefly_dworkers.knowledge.backends import InMemoryKnowledgeBackend, KnowledgeBackend
from firefly_dworkers.knowledge.repository import DocumentChunk, KnowledgeRepository


class TestKnowledgeBackendProtocol:
    """Test that InMemoryKnowledgeBackend satisfies the protocol."""

    def test_is_runtime_checkable(self) -> None:
        backend = InMemoryKnowledgeBackend()
        assert isinstance(backend, KnowledgeBackend)

    def test_set_and_get_fact(self) -> None:
        backend = InMemoryKnowledgeBackend()
        backend.set_fact("key1", {"value": "hello"})
        result = backend.get_fact("key1")
        assert result == {"value": "hello"}

    def test_get_missing_returns_none(self) -> None:
        backend = InMemoryKnowledgeBackend()
        assert backend.get_fact("missing") is None

    def test_iter_items(self) -> None:
        backend = InMemoryKnowledgeBackend()
        backend.set_fact("a", 1)
        backend.set_fact("b", 2)
        items = backend.iter_items()
        keys = {k for k, _ in items}
        assert "a" in keys
        assert "b" in keys

    def test_clear_all(self) -> None:
        backend = InMemoryKnowledgeBackend()
        backend.set_fact("x", "data")
        backend.clear_all()
        assert backend.get_fact("x") is None
        assert backend.iter_items() == []

    def test_custom_memory(self) -> None:
        store = InMemoryStore()
        memory = MemoryManager(store=store, working_scope_id="custom-test")
        backend = InMemoryKnowledgeBackend(memory=memory)
        backend.set_fact("k", "v")
        assert backend.get_fact("k") == "v"
        assert backend.memory is memory

    def test_default_scope_id(self) -> None:
        backend = InMemoryKnowledgeBackend(scope_id="my-scope")
        backend.set_fact("scoped", "data")
        assert backend.get_fact("scoped") == "data"


class TestRepositoryWithBackend:
    """Test KnowledgeRepository with explicit backend parameter."""

    def test_repository_with_custom_backend(self) -> None:
        backend = InMemoryKnowledgeBackend()
        repo = KnowledgeRepository(backend=backend)
        chunk = DocumentChunk(chunk_id="b1", source="s", content="test content")
        repo.index(chunk)
        result = repo.get("b1")
        assert result is not None
        assert result.content == "test content"

    def test_repository_backward_compatible_memory(self) -> None:
        """Passing memory= still works as before."""
        store = InMemoryStore()
        memory = MemoryManager(store=store, working_scope_id="compat")
        repo = KnowledgeRepository(memory=memory)
        repo.index(DocumentChunk(chunk_id="c1", source="s", content="compat test"))
        assert repo.get("c1") is not None
        assert repo.memory is memory

    def test_repository_default_backend(self) -> None:
        """No arguments creates a default InMemoryKnowledgeBackend."""
        repo = KnowledgeRepository()
        repo.index(DocumentChunk(chunk_id="d1", source="s", content="default"))
        assert repo.get("d1") is not None

    def test_backend_takes_priority_over_memory(self) -> None:
        """When both backend and memory are provided, backend wins."""
        backend = InMemoryKnowledgeBackend()
        memory = MemoryManager(working_scope_id="ignored")
        repo = KnowledgeRepository(backend=backend, memory=memory)
        repo.index(DocumentChunk(chunk_id="e1", source="s", content="priority"))
        assert repo.get("e1") is not None
        # The backend we passed is what's used, not the memory
        assert backend.get_fact("doc:e1") is not None
