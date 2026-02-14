# firefly-dworkers Documentation

## Contents

- [Navigation](#navigation)
  - [Getting Started](#getting-started)
  - [Core Concepts](#core-concepts)
  - [Extending the Platform](#extending-the-platform)
  - [API and SDK](#api-and-sdk)
  - [Contributing](#contributing)
- [Quick Links](#quick-links)

---

**Digital Workers as a Service (DWaaS) platform built on fireflyframework-genai for consulting firms.**

---

## Navigation

### Getting Started

- [Getting Started](getting-started.md) -- Installation, configuration, and first run
- [Configuration Reference](configuration.md) -- Complete tenant YAML reference
- [CLI Reference](cli-reference.md) -- All CLI commands with examples

### Core Concepts

- [Architecture](architecture.md) -- Hexagonal architecture deep dive with diagrams
- [Workers](workers/overview.md) -- Worker roles, lifecycle, and instruction building
- [Tools](tools/overview.md) -- Tool system, port/adapter pattern
- [Design Pipeline](design-pipeline.md) -- LLM-powered design intelligence for presentations, documents, and spreadsheets
- [Plans](plans/overview.md) -- DAG-based workflow templates
- [Knowledge](knowledge/overview.md) -- Document indexing and retrieval
- [Tenants](tenants/overview.md) -- Multi-tenant configuration
- [Verticals](verticals/overview.md) -- Industry-specific configurations
- [Autonomy](autonomy/overview.md) -- Autonomy levels and checkpointing

### Extending the Platform

- [Custom Workers](workers/custom-workers.md) -- Creating custom workers via WorkerFactory
- [Tool Registry](tools/registry.md) -- Creating and registering custom tools
- [Custom Plans](plans/custom-plans.md) -- Creating custom workflow templates
- [Plan Templates](plans/templates.md) -- Built-in plan template reference

### API and SDK

- [REST API Reference](api-reference.md) -- FastAPI endpoints documentation
- [SDK Overview](sdk/overview.md) -- Sync and async Python clients

### Contributing

- [Contributing Guide](contributing.md) -- Development setup, testing, and guidelines

---

## Quick Links

| Topic | Module | Key Class |
|-------|--------|-----------|
| Workers | `firefly_dworkers.workers` | `BaseWorker`, `WorkerFactory` |
| Tools | `firefly_dworkers.tools` | `ToolRegistry`, `tool_registry` |
| Design Pipeline | `firefly_dworkers.design` | `DesignEngine`, `TemplateAnalyzer`, `UnifiedDesignPipeline` |
| Plans | `firefly_dworkers.plans` | `BasePlan`, `PlanBuilder` |
| Knowledge | `firefly_dworkers.knowledge` | `KnowledgeRepository`, `KnowledgeBackend` |
| Tenants | `firefly_dworkers.tenants` | `TenantConfig`, `TenantRegistry` |
| Verticals | `firefly_dworkers.verticals` | `VerticalConfig` |
| Autonomy | `firefly_dworkers.autonomy` | `CheckpointStore`, `AutonomyConfig` |
| Prompts | `firefly_dworkers.prompts` | `PromptLoader`, `get_worker_prompt`, `get_skill_prompt` |
| Orchestration | `firefly_dworkers.orchestration` | `ProjectOrchestrator` |
| SDK | `firefly_dworkers.sdk` | `DworkersClient`, `AsyncDworkersClient` |
| Server | `firefly_dworkers_server` | `create_dworkers_app()` |
| CLI | `firefly_dworkers_cli` | `dworkers` command |
