# Architecture

## Contents

- [Layered Overview](#layered-overview)
- [Three Packages, One Repository](#three-packages-one-repository)
- [Port / Adapter Pattern](#port--adapter-pattern)
  - [Port Definitions](#port-definitions)
- [ToolRegistry Flow](#toolregistry-flow)
- [WorkerFactory Flow](#workerfactory-flow)
- [Knowledge Backend Protocol](#knowledge-backend-protocol)
- [Plan DAG Execution](#plan-dag-execution)
- [Tenant Configuration Flow](#tenant-configuration-flow)
- [Prompt Management](#prompt-management)
- [Guards and Observability](#guards-and-observability)
- [Dependency on fireflyframework-genai](#dependency-on-fireflyframework-genai)
- [Threading and Concurrency](#threading-and-concurrency)

---

firefly-dworkers is structured as a **hexagonal architecture** (ports and adapters) built on top of fireflyframework-genai. This document provides a detailed walkthrough of each architectural layer and the key patterns used throughout the system.

---

## Layered Overview

The platform is organized into distinct layers, each with clear responsibilities:

```
+-----------------------------------------------------------+
|                  APPLICATION LAYER                         |
|  firefly_dworkers_server  |  firefly_dworkers_cli         |
|  REST API (FastAPI)       |  CLI (Typer + Rich)           |
+-----------------------------------------------------------+
                            |
+-----------------------------------------------------------+
|                  SDK LAYER                                 |
|  DworkersClient  |  AsyncDworkersClient  |  Models        |
+-----------------------------------------------------------+
                            |
+-----------------------------------------------------------+
|                  ORCHESTRATION LAYER                       |
|  Plans (DAG Templates)  |  PlanBuilder  |  Autonomy       |
+-----------------------------------------------------------+
                            |
+-----------------------------------------------------------+
|                  WORKER LAYER                              |
|  BaseWorker  |  WorkerFactory  |  WorkerRegistry          |
|  AnalystWorker  |  ResearcherWorker  |  DataAnalystWorker  |
|  ManagerWorker                                            |
+-----------------------------------------------------------+
                            |
+-----------------------------------------------------------+
|                  TOOL LAYER                                |
|  ToolRegistry  |  ToolKits  |  Ports + Adapters           |
+-----------------------------------------------------------+
                            |
+-----------------------------------------------------------+
|                  INFRASTRUCTURE LAYER                      |
|  TenantConfig  |  Knowledge  |  Verticals  |  Autonomy    |
+-----------------------------------------------------------+
                            |
+-----------------------------------------------------------+
|                  fireflyframework-genai                    |
|  FireflyAgent  |  BaseTool  |  PipelineBuilder  |  Memory |
+-----------------------------------------------------------+
```

---

## Three Packages, One Repository

The repository contains three Python packages:

| Package | Purpose | Key Entry Point |
|---------|---------|-----------------|
| `firefly_dworkers` | Core library (workers, tools, plans, tenants, knowledge, SDK) | `from firefly_dworkers import ...` |
| `firefly_dworkers_server` | FastAPI application server | `create_dworkers_app()` |
| `firefly_dworkers_cli` | Typer CLI application | `dworkers` command |

---

## Port / Adapter Pattern

The tool layer follows the hexagonal architecture pattern where abstract base classes (ports) define contracts and concrete implementations (adapters) fulfill them.

```mermaid
graph LR
    subgraph "Ports (Abstract Bases)"
        WST["WebSearchTool"]
        WBT["WebBrowsingTool"]
        DST["DocumentStorageTool"]
        MT["MessageTool"]
        PMT["ProjectManagementTool"]
        CT["ConsultingTool"]
        PT["PresentationTool"]
        DT["DocumentTool"]
        SpT["SpreadsheetPort"]
        VT["VisionAnalysisTool"]
    end

    subgraph "Adapters (Concrete)"
        Tavily["TavilySearchTool"]
        SerpAPI["SerpAPISearchTool"]
        WB["WebBrowserTool"]
        FB["FlyBrowserTool"]
        SP["SharePointTool"]
        GD["GoogleDriveTool"]
        Conf["ConfluenceTool"]
        S3["S3Tool"]
        Slack["SlackTool"]
        Teams["TeamsTool"]
        Email["EmailTool"]
        Jira["JiraTool"]
        Asana["AsanaTool"]
        RG["ReportGenerationTool"]
        PM["ProcessMappingTool"]
        GA["GapAnalysisTool"]
        RQ["RequirementGatheringTool"]
        Doc["DocumentationTool"]
        PPT["PowerPointTool"]
        GSlides["GoogleSlidesTool"]
        Word["WordTool"]
        GDocs["GoogleDocsTool"]
        PDF["PDFTool"]
        Excel["ExcelTool"]
        GSheets["GoogleSheetsTool"]
    end

    WST --> Tavily
    WST --> SerpAPI
    WBT --> WB
    WBT --> FB
    DST --> SP
    DST --> GD
    DST --> Conf
    DST --> S3
    MT --> Slack
    MT --> Teams
    MT --> Email
    PMT --> Jira
    PMT --> Asana
    CT --> RG
    CT --> PM
    CT --> GA
    CT --> RQ
    CT --> Doc
    PT --> PPT
    PT --> GSlides
    DT --> Word
    DT --> GDocs
    DT --> PDF
    SpT --> Excel
    SpT --> GSheets
```

### Port Definitions

Each port extends `fireflyframework_genai.tools.base.BaseTool`:

| Port | Module | Abstract Methods |
|------|--------|-----------------|
| `WebSearchTool` | `firefly_dworkers.tools.web.search` | `_search(query, max_results)` |
| `WebBrowsingTool` | `firefly_dworkers.tools.web.browsing` | `_fetch_page(url, extract_links)` |
| `DocumentStorageTool` | `firefly_dworkers.tools.storage.base` | `_search`, `_read`, `_list`, `_write` |
| `MessageTool` | `firefly_dworkers.tools.communication.base` | `_send`, `_read`, `_list_channels` |
| `ProjectManagementTool` | `firefly_dworkers.tools.project.base` | `_create_task`, `_list_tasks`, `_update_task`, `_get_task` |
| `ConsultingTool` | `firefly_dworkers.tools.consulting.base` | Varies per subclass (each implements `_execute`) |
| `PresentationTool` | `firefly_dworkers.tools.presentation.base` | `_create`, `_add_slide`, `_save` |
| `DocumentTool` | `firefly_dworkers.tools.document.base` | `_create`, `_add_section`, `_save` |
| `SpreadsheetPort` | `firefly_dworkers.tools.spreadsheet.base` | `_create`, `_add_sheet`, `_save`, `_read` |

---

## ToolRegistry Flow

The `ToolRegistry` enables self-registration of tool classes at import time through decorators:

```mermaid
sequenceDiagram
    participant Module as Tool Module (e.g. tavily.py)
    participant Decorator as @tool_registry.register()
    participant Registry as ToolRegistry
    participant Toolkit as ToolKit Factory
    participant Worker as Worker Instance

    Module->>Decorator: Class definition
    Decorator->>Registry: Store class under key + category
    Note over Registry: {"tavily": {cls: TavilySearchTool, category: "web_search"}}

    Toolkit->>Registry: tool_registry.create("tavily", api_key="...")
    Registry->>Toolkit: TavilySearchTool(api_key="...")
    Toolkit->>Worker: ToolKit with assembled tools
```

Registration happens at module import time. The `firefly_dworkers.tools.__init__` module imports all concrete tool modules, triggering their `@tool_registry.register()` decorators:

```python
from __future__ import annotations

# Each import triggers self-registration
import firefly_dworkers.tools.web.tavily       # registers "tavily"
import firefly_dworkers.tools.web.serpapi       # registers "serpapi"
import firefly_dworkers.tools.storage.sharepoint  # registers "sharepoint"
# ... and so on for all concrete tools
```

---

## WorkerFactory Flow

Workers use the same decorator-based registration pattern:

```mermaid
sequenceDiagram
    participant Module as Worker Module (e.g. analyst.py)
    participant Decorator as @worker_factory.register()
    participant Factory as WorkerFactory
    participant Builder as PlanBuilder
    participant Worker as AnalystWorker

    Module->>Decorator: Class definition
    Decorator->>Factory: Store class under WorkerRole.ANALYST

    Builder->>Factory: worker_factory.create(WorkerRole.ANALYST, tenant_config, name="...")
    Factory->>Worker: AnalystWorker(tenant_config, name="...")
    Worker->>Worker: Resolve model from tenant_config
    Worker->>Worker: Build instructions with vertical fragments
    Worker->>Worker: Assemble toolkit from enabled connectors
```

Each worker class decorates itself:

```python
from __future__ import annotations

from firefly_dworkers.workers.factory import worker_factory
from firefly_dworkers.types import WorkerRole

@worker_factory.register(WorkerRole.ANALYST)
class AnalystWorker(BaseWorker):
    ...
```

---

## Knowledge Backend Protocol

The knowledge layer uses a protocol-based abstraction to support pluggable storage backends:

```mermaid
graph TB
    subgraph "Protocol"
        KB["KnowledgeBackend (Protocol)"]
    end

    subgraph "Implementations"
        IM["InMemoryKnowledgeBackend"]
        File["FileKnowledgeBackend"]
        PG["PostgresKnowledgeBackend"]
        Mongo["MongoDBKnowledgeBackend"]
    end

    subgraph "Consumers"
        Repo["KnowledgeRepository"]
        Indexer["DocumentIndexer"]
        Retriever["KnowledgeRetriever"]
    end

    KB --> IM
    KB --> File
    KB --> PG
    KB --> Mongo

    Repo --> KB
    Indexer --> Repo
    Retriever --> Repo
```

The `KnowledgeBackend` protocol defines four methods:

| Method | Purpose |
|--------|---------|
| `set_fact(key, value)` | Store a value under a key |
| `get_fact(key)` | Retrieve a value by key |
| `iter_items()` | Return all (key, value) pairs |
| `clear_all()` | Remove all stored data |

Any object implementing these methods satisfies the protocol. The default `InMemoryKnowledgeBackend` wraps the framework's `MemoryManager`.

---

## Plan DAG Execution

Plans are templates that define a directed acyclic graph (DAG) of worker tasks. The `PlanBuilder` converts a plan template into an executable pipeline:

```mermaid
graph TD
    subgraph "Market Analysis Plan"
        S1["define-scope<br/>(Analyst)"]
        S2["research-competitors<br/>(Researcher)"]
        S3["analyze-market-data<br/>(Data Analyst)"]
        S4["assess-opportunities<br/>(Analyst)"]
        S5["strategy-report<br/>(Analyst)"]
        S6["executive-review<br/>(Manager)"]
    end

    S1 --> S2
    S1 --> S3
    S2 --> S4
    S3 --> S4
    S4 --> S5
    S5 --> S6
```

The execution flow:

```mermaid
sequenceDiagram
    participant Client
    participant PlanBuilder
    participant Factory as WorkerFactory
    participant Pipeline as PipelineEngine
    participant Workers as Worker Instances

    Client->>PlanBuilder: PlanBuilder(plan, tenant_config)
    PlanBuilder->>PlanBuilder: build()

    loop For each PlanStep
        PlanBuilder->>Factory: worker_factory.create(step.worker_role, tenant_config)
        Factory->>PlanBuilder: Worker instance
        PlanBuilder->>Pipeline: add_node(step_id, worker)
    end

    loop For each dependency edge
        PlanBuilder->>Pipeline: add_edge(dep_id, step_id)
    end

    PlanBuilder->>Pipeline: build() -> PipelineEngine
    Client->>Pipeline: Execute
    Pipeline->>Workers: Run in DAG order (parallel where possible)
```

Each `PlanStep` specifies:

- `step_id` -- Unique identifier within the plan
- `worker_role` -- Which `WorkerRole` executes this step
- `depends_on` -- List of step IDs that must complete first
- `prompt_template` -- Template for the worker's input
- `retry_max` -- Maximum retry attempts
- `timeout_seconds` -- Execution timeout

---

## Tenant Configuration Flow

Configuration flows from YAML files through the tenant system into workers:

```mermaid
graph LR
    YAML["Tenant YAML"] --> Loader["TenantLoader"]
    Loader --> Config["TenantConfig"]
    Config --> Registry["TenantRegistry"]
    Config --> Factory["WorkerFactory"]
    Config --> Toolkits["ToolKit Factories"]
    Config --> Context["ContextVar (per-request)"]
```

The `TenantConfig` model provides:

- `models` -- Default and purpose-specific LLM model identifiers
- `verticals` -- List of industry vertical names to activate
- `workers` -- Per-role worker settings (autonomy level, custom instructions)
- `connectors` -- Typed configuration for each connector (enabled flag, credentials)
- `knowledge` -- Knowledge source definitions
- `branding` -- Report templates, company name, logo
- `security` -- Allowed models, data residency, encryption settings

---

## Prompt Management

Worker instructions and skill prompts are managed via Jinja2 templates, auto-discovered by `PromptLoader`:

```mermaid
graph LR
    Templates["Jinja2 Templates (.j2)"] --> Loader["PromptLoader"]
    Loader --> Registry["PromptRegistry"]
    Registry --> WorkerPrompt["get_worker_prompt()"]
    Registry --> SkillPrompt["get_skill_prompt()"]
    WorkerPrompt --> Worker["BaseWorker"]
    SkillPrompt --> Tools["Productivity Tools"]
```

Template directories:
- `prompts/workers/` -- Worker system prompts (prefixed `worker/`)
- `prompts/skills/` -- Tool skill prompts (prefixed `skill/`)

---

## Guards and Observability

BaseWorker automatically wires guard and cost middleware from tenant configuration:

- **PromptGuardMiddleware** -- Scans prompts for injection patterns. Supports sanitisation mode (redacts matches) or rejection mode (raises error).
- **OutputGuardMiddleware** -- Scans LLM output for PII, secrets, and harmful content. Blocks or sanitises based on configured categories.
- **CostGuardMiddleware** -- Enforces per-call and total budget limits. Can warn-only or block.
- **LoggingMiddleware** and **ObservabilityMiddleware** -- Auto-wired by the framework.

---

## Dependency on fireflyframework-genai

firefly-dworkers extends the following framework primitives:

| Framework Class | dworkers Extension |
|----------------|-------------------|
| `FireflyAgent` | `BaseWorker` (adds role, autonomy, tenant config) |
| `BaseTool` | `WebSearchTool`, `WebBrowsingTool`, `DocumentStorageTool`, `MessageTool`, `ProjectManagementTool`, `ConsultingTool`, `PresentationTool`, `DocumentTool`, `SpreadsheetPort` |
| `ToolKit` | Per-worker toolkit factories in `toolkits.py` |
| `PipelineBuilder` | `PlanBuilder` wraps it to create DAGs from plan templates |
| `MemoryManager` | `InMemoryKnowledgeBackend` wraps it for document storage |
| `create_genai_app()` | `create_dworkers_app()` extends it with dworkers-specific routes |
| `PromptTemplate` / `PromptRegistry` | `PromptLoader` wraps template discovery and registration |
| `FallbackComposer` / `SequentialComposer` | Resilient tool chains in toolkit factories |
| `PromptGuardMiddleware` / `OutputGuardMiddleware` | Guard middleware wired by `BaseWorker` |
| `CostGuardMiddleware` | Cost tracking middleware wired by `BaseWorker` |

---

## Threading and Concurrency

All registries (`ToolRegistry`, `WorkerFactory`, `WorkerRegistry`, `PlanRegistry`, `TenantRegistry`, `CheckpointStore`) are thread-safe, using `threading.Lock` for all read and write operations. The tenant context uses `contextvars.ContextVar` for per-request isolation in async server environments.

---

## Related Documentation

- [Tools Overview](tools/overview.md) -- tool categories and the port/adapter pattern
- [Tool Registry](tools/registry.md) -- decorator-based tool registration API
- [Workers Overview](workers/overview.md) -- worker roles and lifecycle
- [Custom Workers](workers/custom-workers.md) -- creating workers with WorkerFactory
- [Knowledge Layer](knowledge/overview.md) -- KnowledgeBackend protocol
- [Plans Overview](plans/overview.md) -- DAG-based plan execution
- [Tenants Overview](tenants/overview.md) -- multi-tenancy architecture
