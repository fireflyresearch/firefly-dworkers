# SDK Overview

## Contents

- [Module](#module)
- [Synchronous Client](#synchronous-client)
  - [Constructor Parameters](#constructor-parameters)
  - [Client Methods](#client-methods)
- [Asynchronous Client](#asynchronous-client)
- [Request Models](#request-models)
  - [RunWorkerRequest](#runworkerrequest)
  - [ExecutePlanRequest](#executeplanrequest)
  - [IndexDocumentRequest](#indexdocumentrequest)
  - [SearchKnowledgeRequest](#searchknowledgerequest)
  - [ProjectRequest](#projectrequest)
- [Response Models](#response-models)
  - [WorkerResponse](#workerresponse)
  - [PlanResponse](#planresponse)
  - [IndexResponse](#indexresponse)
  - [SearchResponse](#searchresponse)
  - [KnowledgeChunkResponse](#knowledgechunkresponse)
  - [HealthResponse](#healthresponse)
  - [StreamEvent](#streamevent)
  - [ProjectEvent](#projectevent)
  - [ProjectResponse](#projectresponse)
- [Error Handling](#error-handling)
- [Authentication](#authentication)
- [Related Documentation](#related-documentation)

---

The firefly-dworkers SDK provides synchronous and asynchronous Python clients for programmatic access to the dworkers API server.

---

## Module

```
firefly_dworkers.sdk
```

Key classes:

| Class | Purpose |
|-------|---------|
| `DworkersClient` | Synchronous HTTP client |
| `AsyncDworkersClient` | Asynchronous HTTP client |
| `RunWorkerRequest` | Request model for running a worker |
| `ExecutePlanRequest` | Request model for executing a plan |
| `IndexDocumentRequest` | Request model for indexing a document |
| `SearchKnowledgeRequest` | Request model for searching knowledge |
| `WorkerResponse` | Response from a worker run |
| `PlanResponse` | Response from a plan execution |
| `IndexResponse` | Response from document indexing |
| `SearchResponse` | Response from knowledge search |
| `KnowledgeChunkResponse` | A single chunk in search results |
| `HealthResponse` | Health check response |
| `StreamEvent` | SSE streaming event |
| `ProjectRequest` | Request for project orchestration |
| `ProjectEvent` | SSE event from project orchestration |
| `ProjectResponse` | Sync project response |

---

## Synchronous Client

```python
from __future__ import annotations

from firefly_dworkers.sdk import DworkersClient, RunWorkerRequest

# Use as a context manager for automatic cleanup
with DworkersClient(base_url="http://localhost:8000", api_key="secret") as client:
    # Health check
    health = client.health()
    print(f"Status: {health.status}, Version: {health.version}")

    # Run a worker
    response = client.run_worker(RunWorkerRequest(
        worker_role="researcher",
        prompt="Research AI adoption trends in financial services.",
        tenant_id="acme-corp",
    ))
    print(f"Output: {response.output}")

    # List available plans
    plans = client.list_plans()
    print(f"Plans: {plans}")

    # List registered workers
    workers = client.list_workers()
    print(f"Workers: {workers}")
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `"http://localhost:8000"` | Server base URL |
| `timeout` | `float` | `120.0` | HTTP request timeout in seconds |
| `api_key` | `str` | `""` | Bearer token for authentication |

### Client Methods

Both `DworkersClient` and `AsyncDworkersClient` expose the same set of methods. In the async client, every method is a coroutine (prefix with `await`).

| Method | Request Type | Return Type | Description |
|--------|-------------|-------------|-------------|
| `health()` | -- | `HealthResponse` | Check API health |
| `run_worker(request)` | `RunWorkerRequest` | `WorkerResponse` | Run a digital worker |
| `execute_plan(request)` | `ExecutePlanRequest` | `PlanResponse` | Execute a consulting plan |
| `index_document(request)` | `IndexDocumentRequest` | `IndexResponse` | Index a document into the knowledge base |
| `search_knowledge(request)` | `SearchKnowledgeRequest` | `SearchResponse` | Search the knowledge base |
| `list_plans()` | -- | `list[str]` | List available plan template names |
| `list_workers()` | -- | `list[str]` | List registered worker names |
| `close()` | -- | `None` | Close the underlying HTTP client |

Both clients support context managers for automatic cleanup (`with` for sync, `async with` for async).

---

## Asynchronous Client

```python
from __future__ import annotations

import asyncio

from firefly_dworkers.sdk import AsyncDworkersClient, RunWorkerRequest


async def main() -> None:
    async with AsyncDworkersClient(base_url="http://localhost:8000") as client:
        # Health check
        health = await client.health()
        print(f"Status: {health.status}")

        # Run a worker
        response = await client.run_worker(RunWorkerRequest(
            worker_role="analyst",
            prompt="Analyze the current process for client onboarding.",
            tenant_id="default",
        ))
        print(f"Output: {response.output}")

        # Execute a plan
        from firefly_dworkers.sdk import ExecutePlanRequest

        plan_response = await client.execute_plan(ExecutePlanRequest(
            plan_name="market-analysis",
            tenant_id="default",
            inputs={"target_market": "healthcare AI"},
        ))
        print(f"Success: {plan_response.success}")


asyncio.run(main())
```

The async client has the same API as the sync client, but all methods are `async`.

---

## Request Models

### RunWorkerRequest

Run a specific digital worker with a prompt.

```python
from __future__ import annotations

from firefly_dworkers.sdk import RunWorkerRequest

request = RunWorkerRequest(
    worker_role="researcher",       # "analyst", "researcher", "data_analyst", "manager"
    prompt="Research AI trends...",
    tenant_id="default",            # Tenant ID (default: "default")
    conversation_id=None,           # Optional conversation ID for context
    autonomy_level=None,            # Optional override
    model=None,                     # Optional model override
)
```

### ExecutePlanRequest

Execute a consulting plan template.

```python
from __future__ import annotations

from firefly_dworkers.sdk import ExecutePlanRequest

request = ExecutePlanRequest(
    plan_name="market-analysis",
    tenant_id="default",
    inputs={"target_market": "healthcare AI", "competitors": ["CompanyA", "CompanyB"]},
)
```

### IndexDocumentRequest

Index a document into the knowledge base.

```python
from __future__ import annotations

from firefly_dworkers.sdk import IndexDocumentRequest

request = IndexDocumentRequest(
    source="upload://annual-report-2026.pdf",
    content="<document text content>",
    tenant_id="default",
    metadata={"author": "Finance Team", "year": "2026"},
    chunk_size=1000,         # Characters per chunk
    chunk_overlap=200,       # Overlap between chunks
)
```

### SearchKnowledgeRequest

Search the knowledge base.

```python
from __future__ import annotations

from firefly_dworkers.sdk import SearchKnowledgeRequest

request = SearchKnowledgeRequest(
    query="annual revenue growth",
    tenant_id="default",
    max_results=5,
)
```

### ProjectRequest

Request for multi-agent project orchestration.

```python
from __future__ import annotations

from firefly_dworkers.sdk import ProjectRequest

request = ProjectRequest(
    brief="Analyze the competitive landscape for healthcare AI startups",
    tenant_id="default",
    project_id=None,            # Optional custom project ID (auto-generated if omitted)
    worker_roles=[],            # Optional override of which worker roles to use
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `brief` | `str` | (required) | Project brief/objective |
| `tenant_id` | `str` | `"default"` | Tenant ID |
| `project_id` | `str \| None` | `None` | Custom project ID |
| `worker_roles` | `list[str]` | `[]` | Override which worker roles to use |

---

## Response Models

### WorkerResponse

| Field | Type | Description |
|-------|------|-------------|
| `worker_name` | `str` | Name of the worker that processed the request |
| `role` | `str` | Worker role |
| `output` | `str` | Worker output text |
| `conversation_id` | `str | None` | Conversation ID for follow-up |

### PlanResponse

| Field | Type | Description |
|-------|------|-------------|
| `plan_name` | `str` | Name of the executed plan |
| `success` | `bool` | Whether the plan completed successfully |
| `outputs` | `dict[str, Any]` | Step outputs keyed by step ID |
| `duration_ms` | `float` | Total execution time in milliseconds |

### IndexResponse

| Field | Type | Description |
|-------|------|-------------|
| `chunk_ids` | `list[str]` | IDs of created chunks |
| `source` | `str` | Source identifier |

### SearchResponse

| Field | Type | Description |
|-------|------|-------------|
| `query` | `str` | The search query |
| `results` | `list[KnowledgeChunkResponse]` | Matching chunks |

### KnowledgeChunkResponse

A single knowledge chunk returned as part of a `SearchResponse`.

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `str` | Unique chunk identifier |
| `source` | `str` | Source document identifier |
| `content` | `str` | Chunk text content |
| `metadata` | `dict[str, Any]` | Arbitrary metadata attached to the chunk |

### HealthResponse

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | Server status (e.g., `"ok"`) |
| `version` | `str` | Server version |

### StreamEvent

An SSE streaming event returned during worker or plan execution.

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Event type (e.g., `"token"`, `"complete"`, `"error"`) |
| `content` | `str` | Event content/payload |
| `metadata` | `dict[str, Any]` | Optional metadata attached to the event |

Example:

```json
{"type": "token", "content": "Based on", "metadata": {}}
```

### ProjectEvent

An SSE event returned during project orchestration.

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Event type (e.g., `"project_start"`, `"task_assigned"`, `"task_complete"`, `"worker_output"`, `"project_complete"`, `"error"`) |
| `content` | `str` | Event content/payload |
| `metadata` | `dict[str, Any]` | Optional metadata (e.g., worker role, task ID) |

### ProjectResponse

Synchronous response from project orchestration.

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | `str` | Unique project identifier |
| `success` | `bool` | Whether the project completed successfully |
| `deliverables` | `dict[str, Any]` | Project deliverables keyed by worker role or task |
| `duration_ms` | `float` | Total execution time in milliseconds |

---

## Error Handling

Both clients raise `httpx.HTTPStatusError` for non-2xx responses:

```python
from __future__ import annotations

import httpx
from firefly_dworkers.sdk import DworkersClient, ExecutePlanRequest

with DworkersClient() as client:
    try:
        response = client.execute_plan(ExecutePlanRequest(
            plan_name="nonexistent-plan",
            tenant_id="default",
        ))
    except httpx.HTTPStatusError as e:
        print(f"Error {e.response.status_code}: {e.response.json()}")
```

---

## Authentication

When `api_key` is provided, the client sends it as a Bearer token in the `Authorization` header:

```python
from __future__ import annotations

from firefly_dworkers.sdk import DworkersClient

client = DworkersClient(api_key="your-secret-key")
# All requests include: Authorization: Bearer your-secret-key
```

---

## Related Documentation

- [API Reference](../api-reference.md) -- REST endpoint documentation
- [Getting Started](../getting-started.md) -- Quick start tutorial
