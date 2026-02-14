# Orchestration Overview

## Contents

- [ProjectOrchestrator](#projectorchestrator)
- [Three-Phase Pipeline](#three-phase-pipeline)
- [ProjectWorkspace](#projectworkspace)
- [DelegationRouter](#delegationrouter)
- [Streaming Support](#streaming-support)
- [Related Documentation](#related-documentation)

---

## ProjectOrchestrator

The `ProjectOrchestrator` (`firefly_dworkers.orchestration.orchestrator`) coordinates multi-agent collaboration on consulting projects. Unlike plan-based execution (which follows a predefined DAG), the orchestrator dynamically decomposes project briefs and delegates tasks to specialist workers.

```python
from firefly_dworkers.orchestration.orchestrator import ProjectOrchestrator
from firefly_dworkers.tenants.registry import tenant_registry

config = tenant_registry.get("acme-corp")
orchestrator = ProjectOrchestrator(config, project_id="proj-001")

# Synchronous execution
result = await orchestrator.run("Analyze the competitive landscape for AI advisory services")
# result: {"success": True, "deliverables": {...}, "duration_ms": 12345.0}

# Streaming execution
async for event in orchestrator.run_stream("Analyze the competitive landscape"):
    print(event.type, event.content)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `TenantConfig` | (required) | Tenant configuration for worker creation |
| `project_id` | `str` | `"default"` | Unique project identifier |
| `enable_delegation` | `bool` | `False` | Enable framework DelegationRouter for task routing |

---

## Three-Phase Pipeline

The orchestrator follows a three-phase execution model:

```
Phase 1: Decompose          Phase 2: Execute           Phase 3: Synthesize
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ Manager analyzes │───▶│ Specialist workers   │───▶│ Manager compiles    │
│ the project brief│    │ execute tasks in     │    │ findings into final │
│ and creates tasks│    │ parallel, sharing    │    │ deliverables        │
│                  │    │ via ProjectWorkspace  │    │                     │
└─────────────────┘    └──────────────────────┘    └─────────────────────┘
```

### Phase 1: Decompose

The Manager worker analyzes the project brief and breaks it into discrete tasks. Each task is assigned to a specialist worker role (Researcher, Analyst, Data Analyst, or Designer).

### Phase 2: Execute

Specialist workers execute their assigned tasks. Workers share findings with each other through the `ProjectWorkspace`, which provides a shared fact store scoped to the project.

### Phase 3: Synthesize

The Manager worker collects results from all tasks and synthesizes them into final deliverables. The synthesized output includes cross-references between worker findings.

---

## ProjectWorkspace

`ProjectWorkspace` (`firefly_dworkers.orchestration.workspace`) provides shared memory for inter-worker collaboration within a project:

```python
from firefly_dworkers.orchestration.workspace import ProjectWorkspace

workspace = ProjectWorkspace("proj-001")

# Workers store findings
workspace.set_fact("competitor_analysis", {"top_3": [...]})
workspace.set_fact("market_size", "$4.2B")

# Other workers retrieve context
analysis = workspace.get_fact("competitor_analysis")
context = workspace.get_context()  # Human-readable summary
```

**Methods:**

| Method | Description |
|--------|-------------|
| `set_fact(key, value)` | Store a fact in the workspace |
| `get_fact(key, default)` | Retrieve a fact by key |
| `get_all_facts()` | Get all stored facts as a dict |
| `get_context()` | Get a human-readable summary of all facts |

The workspace wraps the framework's `MemoryManager` with project-scoped storage, ensuring fact isolation between concurrent projects.

---

## DelegationRouter

When `enable_delegation=True`, the orchestrator uses the framework's `DelegationRouter` with a `ContentBasedStrategy` to automatically route tasks to the most appropriate worker based on task content.

This is an optional optimization — by default, the orchestrator uses explicit role assignment from the decomposition phase.

---

## Streaming Support

The orchestrator supports real-time streaming via `run_stream()`, which yields `ProjectEvent` objects:

| Event Type | Description |
|------------|-------------|
| `project_start` | Project execution has begun |
| `phase_start` | A phase (decompose/execute/synthesize) has started |
| `task_start` | A worker task has started |
| `task_complete` | A worker task has completed |
| `phase_complete` | A phase has completed |
| `project_complete` | All phases complete, deliverables ready |
| `error` | An error occurred during execution |

---

## Related Documentation

- [Plans Overview](../plans/overview.md) — DAG-based workflow execution (complementary approach)
- [Workers Overview](../workers/overview.md) — Worker roles used by the orchestrator
- [Architecture](../architecture.md) — System architecture overview
