# REST API Reference

## Contents

- [Server Setup](#server-setup)
- [Base URL](#base-url)
- [Health](#health)
  - [GET /health](#get-health)
- [Workers](#workers)
  - [GET /api/workers](#get-apiworkers)
  - [POST /api/workers/run](#post-apiworkersrun)
- [Plans](#plans)
  - [GET /api/plans](#get-apiplans)
  - [GET /api/plans/{plan_name}](#get-apiplansplan_name)
  - [POST /api/plans/execute](#post-apiplansexecute)
- [Tenants](#tenants)
  - [GET /api/tenants](#get-apitenants)
  - [GET /api/tenants/{tenant_id}](#get-apitenantstenant_id)
- [Knowledge](#knowledge)
  - [POST /api/knowledge/index](#post-apiknowledgeindex)
  - [POST /api/knowledge/search](#post-apiknowledgesearch)
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
| Tenants | `/api/tenants` | `tenants` |
| Knowledge | `/api/knowledge` | `knowledge` |

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
http://localhost:8000/api/tenants
http://localhost:8000/api/knowledge
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

### POST /api/workers/run

Run a digital worker with a prompt.

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

**Response:**

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

### POST /api/plans/execute

Execute a consulting plan.

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

**Response:**

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
    "default": "openai:gpt-4o",
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
