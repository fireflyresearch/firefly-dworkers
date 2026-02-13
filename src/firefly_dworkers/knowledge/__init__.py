"""Knowledge layer -- document indexing and retrieval for consulting workers."""

from firefly_dworkers.knowledge.backends import InMemoryKnowledgeBackend, KnowledgeBackend
from firefly_dworkers.knowledge.indexer import DocumentIndexer
from firefly_dworkers.knowledge.repository import DocumentChunk, KnowledgeRepository
from firefly_dworkers.knowledge.retriever import KnowledgeRetriever

__all__ = [
    "DocumentChunk",
    "DocumentIndexer",
    "InMemoryKnowledgeBackend",
    "KnowledgeBackend",
    "KnowledgeRepository",
    "KnowledgeRetriever",
]
