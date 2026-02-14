# Custom Plans

This guide covers creating, registering, and executing custom plan templates.

---

## Creating a Plan

A plan is a `BasePlan` with a list of `PlanStep` instances that define the DAG:

```python
from firefly_dworkers.plans.base import BasePlan, PlanStep
from firefly_dworkers.types import WorkerRole


def compliance_audit_plan() -> BasePlan:
    plan = BasePlan(
        "compliance-audit",
        description="Audit regulatory compliance and generate remediation plan",
    )

    plan.add_step(
        PlanStep(
            step_id="scope-audit",
            name="Scope Audit",
            description="Define audit scope, regulations, and assessment criteria",
            worker_role=WorkerRole.ANALYST,
        )
    )
    plan.add_step(
        PlanStep(
            step_id="research-regulations",
            name="Research Regulations",
            description="Research applicable regulations and recent enforcement actions",
            worker_role=WorkerRole.RESEARCHER,
            depends_on=["scope-audit"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="analyze-gaps",
            name="Analyze Compliance Gaps",
            description="Analyze current compliance posture against regulatory requirements",
            worker_role=WorkerRole.DATA_ANALYST,
            depends_on=["scope-audit"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="remediation-plan",
            name="Remediation Plan",
            description="Build prioritized remediation roadmap from gap analysis",
            worker_role=WorkerRole.ANALYST,
            depends_on=["research-regulations", "analyze-gaps"],
        )
    )
    plan.add_step(
        PlanStep(
            step_id="executive-briefing",
            name="Executive Briefing",
            description="Present audit findings and remediation plan to leadership",
            worker_role=WorkerRole.MANAGER,
            depends_on=["remediation-plan"],
        )
    )

    return plan
```

### Key Design Rules

1. **Each step needs a unique `step_id`** within the plan
2. **`depends_on` references must point to existing step IDs** — the builder validates this
3. **The DAG must be acyclic** — circular dependencies cause a build error
4. **Steps without dependencies run in parallel** when executed

---

## Registering a Plan

Register plans with the `PlanRegistry` singleton:

```python
from firefly_dworkers.plans.registry import plan_registry

plan = compliance_audit_plan()
plan_registry.register(plan)

# Now retrievable by name
plan_registry.get("compliance-audit")
plan_registry.list_plans()  # ["compliance-audit", ...]
```

For automatic registration at import time, register in your module's top level:

```python
# my_plans/compliance.py
from firefly_dworkers.plans.registry import plan_registry

plan_registry.register(compliance_audit_plan())
```

---

## Executing a Plan

Use `PlanBuilder` to convert a registered plan into an executable pipeline:

```python
from firefly_dworkers.plans.builder import PlanBuilder
from firefly_dworkers.plans.registry import plan_registry
from firefly_dworkers.tenants.registry import tenant_registry

# Load plan and tenant config
plan = plan_registry.get("compliance-audit")
config = tenant_registry.get("acme-corp")

# Build and execute
builder = PlanBuilder(plan, config)
engine = builder.build()
result = await engine.run(inputs={"brief": "Audit SOX compliance for Q4"})

# Inspect results
print(result.success)           # True/False
print(result.total_duration_ms) # Execution time
for node_id, node_result in result.outputs.items():
    print(f"{node_id}: {node_result.output}")
```

### PlanStep Options

| Field | Purpose | Example |
|-------|---------|---------|
| `prompt_template` | Template for worker input | `"Research {topic} in {geography}"` |
| `retry_max` | Auto-retry on failure | `2` (retry up to 2 times) |
| `timeout_seconds` | Per-step timeout | `300.0` (5-minute limit) |

### Prompt Templates

Use `prompt_template` to parameterize step inputs:

```python
PlanStep(
    step_id="research",
    name="Research Phase",
    worker_role=WorkerRole.RESEARCHER,
    prompt_template="Research {topic} with focus on {focus_area}",
)
```

Pass template variables via the `inputs` dict at execution time:

```python
result = await engine.run(inputs={
    "topic": "cloud migration",
    "focus_area": "cost optimization",
})
```

---

## Related Documentation

- [Plans Overview](overview.md) — Core concepts and execution flow
- [Plan Templates](templates.md) — Built-in template reference
- [Workers Overview](../workers/overview.md) — Available worker roles
