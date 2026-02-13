"""Synchronous client for the dworkers API."""

from __future__ import annotations

from typing import Any

import httpx

from firefly_dworkers.sdk.models import (
    ExecutePlanRequest,
    HealthResponse,
    IndexDocumentRequest,
    IndexResponse,
    PlanResponse,
    RunWorkerRequest,
    SearchKnowledgeRequest,
    SearchResponse,
    WorkerResponse,
)


class DworkersClient:
    """Synchronous client for the dworkers API.

    Usage::

        with DworkersClient(base_url="http://localhost:8000", api_key="secret") as client:
            resp = client.health()
            print(resp.status)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        *,
        timeout: float = 120.0,
        api_key: str = "",
    ) -> None:
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    # -- API methods --------------------------------------------------------

    def health(self) -> HealthResponse:
        """Check API health."""
        resp = self._client.get("/health")
        resp.raise_for_status()
        return HealthResponse.model_validate(resp.json())

    def run_worker(self, request: RunWorkerRequest) -> WorkerResponse:
        """Run a digital worker."""
        resp = self._client.post("/api/workers/run", json=request.model_dump(exclude_none=True))
        resp.raise_for_status()
        return WorkerResponse.model_validate(resp.json())

    def execute_plan(self, request: ExecutePlanRequest) -> PlanResponse:
        """Execute a consulting plan."""
        resp = self._client.post("/api/plans/execute", json=request.model_dump())
        resp.raise_for_status()
        return PlanResponse.model_validate(resp.json())

    def index_document(self, request: IndexDocumentRequest) -> IndexResponse:
        """Index a document into the knowledge base."""
        resp = self._client.post("/api/knowledge/index", json=request.model_dump())
        resp.raise_for_status()
        return IndexResponse.model_validate(resp.json())

    def search_knowledge(self, request: SearchKnowledgeRequest) -> SearchResponse:
        """Search the knowledge base."""
        resp = self._client.post("/api/knowledge/search", json=request.model_dump())
        resp.raise_for_status()
        return SearchResponse.model_validate(resp.json())

    def list_plans(self) -> list[str]:
        """List available plans."""
        resp = self._client.get("/api/plans")
        resp.raise_for_status()
        return resp.json()

    def list_workers(self) -> list[str]:
        """List available workers."""
        resp = self._client.get("/api/workers")
        resp.raise_for_status()
        return resp.json()

    # -- Lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> DworkersClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
