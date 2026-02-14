# firefly-dworkers Documentation

Welcome to the firefly-dworkers documentation. This guide covers everything from
getting started to extending the platform with custom workers and tools.

## Reading Paths

| I want to...                              | Start here                                    |
|-------------------------------------------|-----------------------------------------------|
| Get up and running quickly                | [Getting Started](getting-started.md)         |
| Understand the architecture               | [Architecture](architecture.md)               |
| Generate presentations, documents, or spreadsheets | [Design Pipeline](design-pipeline.md) |
| Configure a tenant                        | [Configuration Reference](configuration.md)   |
| Use the CLI                               | [CLI Reference](cli-reference.md)             |
| Integrate via the REST API                | [API Reference](api-reference.md)             |
| Build a custom worker                     | [Custom Workers](workers/custom-workers.md)   |
| Build a custom tool                       | [Tool Registry](tools/registry.md)            |
| Create a workflow plan                    | [Custom Plans](plans/custom-plans.md)         |
| Contribute to the project                 | [Contributing](contributing.md)               |
| Run the working examples                  | [Examples](../examples/)                      |

## Documentation Map

### Core Concepts
- [Architecture](architecture.md) — Hexagonal architecture, layers, and key patterns
- [Workers](workers/overview.md) — Analyst, Researcher, DataAnalyst, Manager, Designer roles
- [Tools](tools/overview.md) — 33 pluggable connectors across 11 categories with port/adapter pattern
- [Design Pipeline](design-pipeline.md) — LLM-powered design intelligence for PPTX, DOCX, XLSX, and PDF
- [Plans](plans/overview.md) — DAG-based multi-worker workflow templates
- [Knowledge](knowledge/overview.md) — Document indexing and semantic retrieval
- [Tenants](tenants/overview.md) — Multi-tenant configuration and isolation
- [Verticals](verticals/overview.md) — Industry-specific prompt tuning
- [Autonomy](autonomy/overview.md) — Manual, semi-supervised, and autonomous modes
- [Orchestration](orchestration/overview.md) — ProjectOrchestrator multi-agent collaboration

### Reference
- [Configuration](configuration.md) — Complete tenant YAML schema
- [CLI Reference](cli-reference.md) — `dworkers init`, `serve`, `install`, `check`
- [API Reference](api-reference.md) — FastAPI REST endpoints
- [SDK Overview](sdk/overview.md) — Sync and async Python clients

### Extending
- [Custom Workers](workers/custom-workers.md) — WorkerFactory registration
- [Tool Registry](tools/registry.md) — `@tool_registry.register()` decorator
- [Custom Plans](plans/custom-plans.md) — PlanBuilder API
- [Plan Templates](plans/templates.md) — Built-in templates reference

## Version

This documentation covers **firefly-dworkers v26.02.01** (Alpha).
