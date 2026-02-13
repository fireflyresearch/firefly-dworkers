# Getting Started

## Contents

- [Prerequisites](#prerequisites)
- [Step 1: Install](#step-1-install)
- [Step 2: Initialize a Project](#step-2-initialize-a-project)
- [Step 3: Configure Your Tenant](#step-3-configure-your-tenant)
- [Step 4: Start the Server](#step-4-start-the-server)
- [Step 5: Run a Worker](#step-5-run-a-worker)
  - [Via the SDK (Python)](#via-the-sdk-python)
  - [Via the REST API (curl)](#via-the-rest-api-curl)
- [Step 6: Execute a Plan](#step-6-execute-a-plan)
- [Step 7: Index Knowledge](#step-7-index-knowledge)
- [Next Steps](#next-steps)

---

This guide walks you through installing firefly-dworkers, configuring a tenant, and running your first digital worker.

---

## Prerequisites

- Python 3.13 or later
- `pip` or `uv` package manager
- An API key for your chosen LLM provider (e.g., OpenAI, Anthropic)
- (Optional) API keys for connectors you plan to use (Tavily, Slack, Jira, etc.)

---

## Step 1: Install

The recommended way to install is via the interactive installer:

```bash
curl -fsSL https://raw.githubusercontent.com/fireflyresearch/firefly-dworkers/main/install.sh | bash
```

The installer will guide you through choosing an install location and a profile (Minimal, Analyst, Server, Full, or Custom). It bootstraps `uv` if needed and creates an isolated Python 3.13 virtual environment.

For non-interactive environments (CI, scripts):

```bash
# Full profile, no prompts
curl -fsSL https://raw.githubusercontent.com/fireflyresearch/firefly-dworkers/main/install.sh | bash -s -- --yes --profile full

# Custom prefix
curl -fsSL .../install.sh | bash -s -- --yes --profile analyst --prefix /opt/dworkers
```

To uninstall:

```bash
dworkers-uninstall
```

### Alternative: pip / uv

If you prefer traditional Python package management:

```bash
pip install firefly-dworkers[all]
```

Or install only what you need:

```bash
# Core library only (no connectors, no server)
pip install firefly-dworkers

# Core + server + CLI
pip install firefly-dworkers[server,cli]

# Core + specific connectors
pip install firefly-dworkers[web,slack,jira]
```

If you use `uv`:

```bash
uv add firefly-dworkers[all]
```

---

## Step 2: Initialize a Project

Use the CLI to scaffold a new project:

```bash
dworkers init my-project
```

This creates a project directory with the following structure:

```
my-project/
|-- config/
|   |-- tenants/
|       |-- default.yaml
|-- .env
```

The `default.yaml` file contains a minimal tenant configuration. The `.env` file is where you place API keys and credentials.

---

## Step 3: Configure Your Tenant

Edit `config/tenants/default.yaml` to match your environment:

```yaml
id: default
name: My Organization

models:
  default: openai:gpt-4o

verticals:
  - technology

workers:
  analyst:
    autonomy: semi_supervised
  researcher:
    autonomy: semi_supervised
  data_analyst:
    autonomy: semi_supervised
  manager:
    autonomy: semi_supervised

connectors:
  web_search:
    enabled: true
    provider: tavily
    api_key: "${TAVILY_API_KEY}"
```

Set environment variables for credentials:

```bash
export TAVILY_API_KEY="tvly-..."
export OPENAI_API_KEY="sk-..."
```

See [Configuration Reference](configuration.md) for the complete schema.

---

## Step 4: Start the Server

Launch the API server:

```bash
dworkers serve
```

The server starts at `http://0.0.0.0:8000` by default. Visit `http://localhost:8000/docs` for the interactive OpenAPI documentation.

---

## Step 5: Run a Worker

### Via the SDK (Python)

```python
from __future__ import annotations

from firefly_dworkers.sdk import DworkersClient, RunWorkerRequest

with DworkersClient(base_url="http://localhost:8000") as client:
    # Check health
    health = client.health()
    print(f"Server status: {health.status}")

    # Run a researcher worker
    response = client.run_worker(
        RunWorkerRequest(
            worker_role="researcher",
            prompt="Research the current state of AI adoption in healthcare consulting.",
            tenant_id="default",
        )
    )
    print(f"Worker: {response.worker_name}")
    print(f"Output: {response.output}")
```

### Via the REST API (curl)

```bash
# Check health
curl http://localhost:8000/health

# List available plans
curl http://localhost:8000/api/plans

# Run a worker
curl -X POST http://localhost:8000/api/workers/run \
  -H "Content-Type: application/json" \
  -d '{
    "worker_role": "researcher",
    "prompt": "Research AI adoption in healthcare consulting.",
    "tenant_id": "default"
  }'
```

---

## Step 6: Execute a Plan

Plans orchestrate multiple workers in a DAG:

```python
from __future__ import annotations

from firefly_dworkers.sdk import DworkersClient, ExecutePlanRequest

with DworkersClient(base_url="http://localhost:8000") as client:
    # List available plans
    plans = client.list_plans()
    print(f"Available plans: {plans}")

    # Execute a market analysis plan
    response = client.execute_plan(
        ExecutePlanRequest(
            plan_name="market-analysis",
            tenant_id="default",
            inputs={"target_market": "AI consulting tools"},
        )
    )
    print(f"Plan: {response.plan_name}")
    print(f"Success: {response.success}")
```

---

## Step 7: Index Knowledge

Load documents into the knowledge base for workers to reference:

```python
from __future__ import annotations

from firefly_dworkers.sdk import (
    DworkersClient,
    IndexDocumentRequest,
    SearchKnowledgeRequest,
)

with DworkersClient(base_url="http://localhost:8000") as client:
    # Index a document
    index_resp = client.index_document(
        IndexDocumentRequest(
            source="internal://company-strategy-2026.pdf",
            content="Our company strategy for 2026 focuses on three pillars...",
            tenant_id="default",
            metadata={"author": "Strategy Team", "year": "2026"},
        )
    )
    print(f"Indexed chunks: {index_resp.chunk_ids}")

    # Search the knowledge base
    search_resp = client.search_knowledge(
        SearchKnowledgeRequest(
            query="company strategy pillars",
            tenant_id="default",
            max_results=5,
        )
    )
    for result in search_resp.results:
        print(f"  [{result.source}] {result.content[:100]}...")
```

---

## Next Steps

- [Working Examples](../examples/) -- Six runnable scripts demonstrating workers, plans, streaming, and tool usage
- [Architecture](architecture.md) -- Understand the hexagonal architecture
- [Workers](workers/overview.md) -- Deep dive into worker roles
- [Tools](tools/overview.md) -- Explore the tool system
- [Plans](plans/overview.md) -- Learn about DAG-based workflows
- [Configuration](configuration.md) -- Complete tenant YAML reference
- [CLI Reference](cli-reference.md) -- All CLI commands
