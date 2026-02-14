# REST API Reference

## Contents

- [Server Setup](#server-setup)
- [Base URL](#base-url)
- [Health](#health)
  - [GET /health](#get-health)
- [Workers](#workers)
  - [GET /api/workers](#get-apiworkers)
  - [POST /api/workers/run (Streaming)](#post-apiworkersrun-streaming)
  - [POST /api/workers/run/sync](#post-apiworkersrunsync)
- [Plans](#plans)
  - [GET /api/plans](#get-apiplans)
  - [GET /api/plans/{plan_name}](#get-apiplansplan_name)
  - [POST /api/plans/execute (Streaming)](#post-apiplansexecute-streaming)
  - [POST /api/plans/execute/sync](#post-apiplansexecutesync)
- [Projects](#projects)
  - [POST /api/projects/run (Streaming)](#post-apiprojectsrun-streaming)
  - [POST /api/projects/run/sync](#post-apiprojectsrunsync)
- [Tenants](#tenants)
  - [GET /api/tenants](#get-apitenants)
  - [GET /api/tenants/{tenant_id}](#get-apitenantstenant_id)
- [Knowledge](#knowledge)
  - [POST /api/knowledge/index](#post-apiknowledgeindex)
  - [POST /api/knowledge/search](#post-apiknowledgesearch)
- [Observability](#observability)
  - [GET /api/observability/usage](#get-apiobservabilityusage)
  - [GET /api/observability/usage/{agent_name}](#get-apiobservabilityusageagent_name)
- [Authentication](#authentication)
- [Error Format](#error-format)
- [OpenAPI Documentation](#openapi-documentation)
- [Related Documentation](#related-documentation)

---

The firefly-dworkers server exposes a REST API built on FastAPI, extending the fireflyframework-genai base application with domain-specific endpoints for workers, plans, tenants, and knowledge management.

---

## Server Setup

The server is created by `create_dworkers_app()` in `firefly_dworkers_server.app`. This factory function extends the framework's `create_genai_app` with dworkers-specific routers for workers, plans, tenants, and knowledge.

```python
from __future__ import annotations

from firefly_dworkers_server.app import create_dworkers_app

app = create_dworkers_app(title="Firefly Dworkers", version="0.1.0")
```

**Factory parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str` | `"Firefly Dworkers"` | Application title for OpenAPI docs |
| `version` | `str` | `"0.1.0"` | Application version string |

**Router prefixes:**

| Router | Prefix | Tags |
|--------|--------|------|
| Workers | `/api/workers` | `workers` |
| Plans | `/api/plans` | `plans` |
| Projects | `/api/projects` | `projects` |
| Tenants | `/api/tenants` | `tenants` |
| Knowledge | `/api/knowledge` | `knowledge` |
| Observability | `/api/observability` | `observability` |

Start the server:

```bash
# Via CLI
dworkers serve

# Via Python module
python -m firefly_dworkers_server

# Via uvicorn directly (factory mode)
uvicorn firefly_dworkers_server.app:create_dworkers_app --host 0.0.0.0 --port 8000 --factory
```

Interactive API documentation is available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc).

---

## Base URL

All dworkers-specific endpoints are prefixed with `/api/`.

```
http://localhost:8000/api/workers
http://localhost:8000/api/plans
http://localhost:8000/api/projects
http://localhost:8000/api/tenants
http://localhost:8000/api/knowledge
http://localhost:8000/api/observability
```

The health endpoint is at the root:

```
http://localhost:8000/health
```

---

## Health

### GET /health

Check API health status.

**Response:**

```json
{
  "status": "ok",
  "version": "26.02.01"
}
```

---

## Workers

### GET /api/workers

List registered worker names.

**Response:**

```json
["analyst-acme-corp", "researcher-acme-corp", "data-analyst-acme-corp"]
```

### POST /api/workers/run (Streaming)

Run a worker with SSE streaming. Returns token-by-token events.

**Request body:**

```json
{
  "worker_role": "researcher",
  "prompt": "Research AI adoption trends in financial services.",
  "tenant_id": "default",
  "conversation_id": null,
  "autonomy_level": null,
  "model": null
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `worker_role` | `string` | Yes | | One of: `analyst`, `researcher`, `data_analyst`, `manager` |
| `prompt` | `string` | Yes | | The prompt to send to the worker |
| `tenant_id` | `string` | No | `"default"` | Tenant ID |
| `conversation_id` | `string` | No | `null` | ID for conversation continuity |
| `autonomy_level` | `string` | No | `null` | Override autonomy level |
| `model` | `string` | No | `null` | Override model |

**Response:** Server-Sent Events (SSE) stream

Event types:

| Event Type | Description |
|------------|-------------|
| `token` | An incremental text token |
| `complete` | Full output after all tokens streamed |
| `error` | Error during execution |

Each event is a JSON `StreamEvent`:

```json
{"type": "token", "content": "Based on", "metadata": {}}
```

### POST /api/workers/run/sync

Run a worker synchronously (non-streaming). Same request body as /run.

**Response:** `WorkerResponse` JSON.

```json
{
  "worker_name": "researcher-worker",
  "role": "researcher",
  "output": "Based on my research, AI adoption in financial services...",
  "conversation_id": null
}
```

---

## Plans

### GET /api/plans

List available plan template names.

**Response:**

```json
["customer-segmentation", "market-analysis", "process-improvement", "technology-assessment"]
```

### GET /api/plans/{plan_name}

Get plan details by name.

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `plan_name` | `string` | Plan template name |

**Response:**

```json
{
  "name": "market-analysis",
  "description": "Research competitors, analyze market size, and generate strategy report",
  "steps": [
    {
      "step_id": "define-scope",
      "name": "Define Scope",
      "description": "Define target markets, geographies, and competitive landscape boundaries",
      "worker_role": "analyst",
      "prompt_template": "",
      "depends_on": [],
      "retry_max": 0,
      "timeout_seconds": 0.0
    },
    {
      "step_id": "research-competitors",
      "name": "Competitive Research",
      "description": "Research key competitors, their offerings, strengths, and weaknesses",
      "worker_role": "researcher",
      "prompt_template": "",
      "depends_on": ["define-scope"],
      "retry_max": 0,
      "timeout_seconds": 0.0
    }
  ]
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Plan not found |

### POST /api/plans/execute (Streaming)

Execute a plan with SSE streaming. Streams pipeline progress events.

**Request body:**

```json
{
  "plan_name": "market-analysis",
  "tenant_id": "default",
  "inputs": {
    "target_market": "healthcare AI",
    "competitors": ["CompanyA", "CompanyB"]
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `plan_name` | `string` | Yes | | Plan template to execute |
| `tenant_id` | `string` | No | `"default"` | Tenant ID |
| `inputs` | `object` | No | `{}` | Input parameters for the plan |

**Response:** Server-Sent Events (SSE) stream

Event types:

| Event Type | Description |
|------------|-------------|
| `node_start` | A pipeline node has started |
| `node_complete` | A pipeline node has completed |
| `node_error` | A pipeline node failed |
| `node_skip` | A pipeline node was skipped |
| `pipeline_complete` | Pipeline execution finished |
| `error` | General error |

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Plan not found |

### POST /api/plans/execute/sync

Execute a plan synchronously. Same request body as /execute.

**Response:** `PlanResponse` JSON.

```json
{
  "plan_name": "market-analysis",
  "success": true,
  "outputs": {
    "status": "completed",
    "define-scope": "...",
    "research-competitors": "..."
  },
  "duration_ms": 45230.5
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Plan not found |

---

## Projects

### POST /api/projects/run (Streaming)

Run a multi-agent project with SSE streaming.

**Request body:**

```json
{
  "brief": "Analyze the competitive landscape for healthcare AI startups",
  "tenant_id": "default",
  "project_id": null,
  "worker_roles": []
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `brief` | `string` | Yes | | Project brief/objective |
| `tenant_id` | `string` | No | `"default"` | Tenant ID |
| `project_id` | `string` | No | auto-generated | Custom project ID |
| `worker_roles` | `array` | No | `[]` | Override which worker roles to use |

**Response:** SSE stream of `ProjectEvent` objects:

| Event Type | Description |
|------------|-------------|
| `project_start` | Orchestration has begun |
| `task_assigned` | Task assigned to a worker |
| `task_complete` | Worker completed a task |
| `worker_output` | Incremental worker output |
| `project_complete` | Project finished |
| `error` | Error during orchestration |

### POST /api/projects/run/sync

Run a project synchronously.

**Response:**

```json
{
  "project_id": "uuid",
  "success": true,
  "deliverables": {},
  "duration_ms": 12345.6
}
```

---

## Tenants

### GET /api/tenants

List registered tenant IDs.

**Response:**

```json
["acme-corp", "globex-inc", "default"]
```

### GET /api/tenants/{tenant_id}

Get tenant configuration by ID.

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tenant_id` | `string` | Tenant identifier |

**Response:**

```json
{
  "id": "acme-corp",
  "name": "Acme Corporation",
  "models": {
    "default": "openai:gpt-5.2",
    "research": "",
    "analysis": ""
  },
  "verticals": ["banking", "technology"],
  "workers": {
    "analyst": {
      "enabled": true,
      "autonomy": "semi_supervised",
      "custom_instructions": "",
      "max_concurrent_tasks": 10
    }
  },
  "connectors": { "..." : "..." },
  "knowledge": { "sources": [] },
  "branding": {
    "company_name": "Acme Corporation",
    "report_template": "default",
    "logo_url": ""
  },
  "security": {
    "allowed_models": ["openai:*", "anthropic:*"],
    "data_residency": "",
    "encryption_enabled": false
  }
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Tenant not found |

---

## Knowledge

### POST /api/knowledge/index

Index a document into the knowledge base.

**Request body:**

```json
{
  "source": "upload://annual-report-2026.pdf",
  "content": "Our company revenue grew 15% year-over-year...",
  "tenant_id": "default",
  "metadata": {
    "author": "Finance Team",
    "year": "2026"
  },
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `source` | `string` | Yes | | Source identifier |
| `content` | `string` | Yes | | Document text content |
| `tenant_id` | `string` | No | `"default"` | Tenant ID |
| `metadata` | `object` | No | `{}` | Arbitrary metadata |
| `chunk_size` | `integer` | No | `1000` | Characters per chunk |
| `chunk_overlap` | `integer` | No | `200` | Overlap between chunks |

**Response:**

```json
{
  "chunk_ids": [
    "upload://annual-report-2026.pdf:0",
    "upload://annual-report-2026.pdf:1",
    "upload://annual-report-2026.pdf:2"
  ],
  "source": "upload://annual-report-2026.pdf"
}
```

### POST /api/knowledge/search

Search the knowledge base.

**Request body:**

```json
{
  "query": "revenue growth",
  "tenant_id": "default",
  "max_results": 5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | `string` | Yes | | Search query |
| `tenant_id` | `string` | No | `"default"` | Tenant ID |
| `max_results` | `integer` | No | `5` | Maximum results to return |

**Response:**

```json
{
  "query": "revenue growth",
  "results": [
    {
      "chunk_id": "upload://annual-report-2026.pdf:0",
      "source": "upload://annual-report-2026.pdf",
      "content": "Our company revenue grew 15% year-over-year...",
      "metadata": {
        "author": "Finance Team",
        "year": "2026"
      }
    }
  ]
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | `string` | The search query that was executed |
| `results` | `array` | List of matching knowledge chunks |
| `results[].chunk_id` | `string` | Unique chunk identifier |
| `results[].source` | `string` | Source document identifier |
| `results[].content` | `string` | Chunk text content |
| `results[].metadata` | `object` | Arbitrary metadata attached to the chunk |

---

## Observability

### GET /api/observability/usage

Get global usage metrics (tokens, cost, requests).

**Response:**

```json
{
  "total_tokens": 15000,
  "total_cost_usd": 0.045,
  "total_requests": 12,
  "total_latency_ms": 8500.0,
  "by_agent": {"analyst-worker": {}},
  "by_model": {"openai:gpt-5.2": {}}
}
```

### GET /api/observability/usage/{agent_name}

Get usage metrics for a specific agent/worker.

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_name` | `string` | Worker/agent name |

**Response:**

```json
{
  "total_tokens": 5000,
  "total_cost_usd": 0.015,
  "total_requests": 4,
  "total_latency_ms": 3200.0
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 404 | Agent not found |

---

## Authentication

When authentication is enabled, pass a Bearer token in the `Authorization` header:

```
Authorization: Bearer <your-api-key>
```

Example with `curl`:

```bash
curl -H "Authorization: Bearer secret-key" http://localhost:8000/api/workers
```

See the [SDK Overview](sdk/overview.md) for how the Python client handles authentication automatically via the `api_key` constructor parameter.

---

## Error Format

All error responses follow the standard FastAPI format:

```json
{
  "detail": "Plan 'nonexistent-plan' not found. Registered: ['market-analysis', 'customer-segmentation', 'process-improvement', 'technology-assessment']"
}
```

---

## OpenAPI Documentation

The server automatically generates OpenAPI documentation accessible at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Related Documentation

- [SDK Overview](sdk/overview.md) -- Python client for the API
- [Getting Started](getting-started.md) -- Tutorial with API examples
- [Configuration](configuration.md) -- Server and tenant configuration
