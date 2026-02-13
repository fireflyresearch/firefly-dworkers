"""Knowledge API router -- index documents and search the knowledge base."""

from __future__ import annotations

from fastapi import APIRouter

from firefly_dworkers.knowledge import DocumentIndexer, KnowledgeRepository, KnowledgeRetriever
from firefly_dworkers.sdk.models import (
    IndexDocumentRequest,
    IndexResponse,
    KnowledgeChunkResponse,
    SearchKnowledgeRequest,
    SearchResponse,
)

router = APIRouter()

# Module-level knowledge stores keyed by tenant_id.
# In production this would be backed by persistent storage per tenant.
_repositories: dict[str, KnowledgeRepository] = {}


def _get_repo(tenant_id: str) -> KnowledgeRepository:
    """Get or create a knowledge repository for the given tenant."""
    if tenant_id not in _repositories:
        _repositories[tenant_id] = KnowledgeRepository()
    return _repositories[tenant_id]


@router.post("/index")
async def index_document(request: IndexDocumentRequest) -> IndexResponse:
    """Index a document into the knowledge base."""
    repo = _get_repo(request.tenant_id)
    indexer = DocumentIndexer(chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap)
    chunk_ids = indexer.index_text(
        request.source,
        request.content,
        metadata=request.metadata,
        repository=repo,
    )
    return IndexResponse(chunk_ids=chunk_ids, source=request.source)


@router.post("/search")
async def search_knowledge(request: SearchKnowledgeRequest) -> SearchResponse:
    """Search the knowledge base."""
    repo = _get_repo(request.tenant_id)
    retriever = KnowledgeRetriever(repo)
    chunks = retriever.retrieve(request.query, max_results=request.max_results)
    return SearchResponse(
        query=request.query,
        results=[
            KnowledgeChunkResponse(
                chunk_id=c.chunk_id,
                source=c.source,
                content=c.content,
                metadata=c.metadata,
            )
            for c in chunks
        ],
    )
