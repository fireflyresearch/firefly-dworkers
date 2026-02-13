# Custom Workers

## Contents

- [Creating a Custom Worker](#creating-a-custom-worker)
  - [Step 1: Define a New Role (Optional)](#step-1-define-a-new-role-optional)
  - [Step 2: Create the Worker Class](#step-2-create-the-worker-class)
  - [Step 3: Import the Module](#step-3-import-the-module)
  - [Step 4: Use the Worker](#step-4-use-the-worker)
- [Creating a Custom Toolkit](#creating-a-custom-toolkit)
- [Overriding an Existing Role](#overriding-an-existing-role)
- [Testing Custom Workers](#testing-custom-workers)
- [Related Documentation](#related-documentation)

---

firefly-dworkers provides four built-in worker roles, but you can create custom workers for specialized consulting needs by extending `BaseWorker` and registering them with the `WorkerFactory`.

---

## Creating a Custom Worker

### Step 1: Define a New Role (Optional)

If your worker represents a genuinely new role rather than a specialization of an existing one, you may want to extend the `WorkerRole` enum. However, for most cases, you can work within the existing roles or use a custom string identifier.

### Step 2: Create the Worker Class

```python
from __future__ import annotations

from typing import Any

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.toolkits import analyst_toolkit
from firefly_dworkers.types import AutonomyLevel, WorkerRole
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.factory import worker_factory


@worker_factory.register(WorkerRole.ANALYST)  # or a custom role
class ComplianceAnalystWorker(BaseWorker):
    """Specialized worker for regulatory compliance analysis.

    Extends the standard analyst with compliance-specific instructions
    and a tailored toolkit.
    """

    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        name: str = "",
        autonomy_level: AutonomyLevel | None = None,
        **kwargs: Any,
    ) -> None:
        toolkit = analyst_toolkit(tenant_config)
        worker_name = name or f"compliance-analyst-{tenant_config.id}"
        instructions = self._build_instructions(tenant_config)

        super().__init__(
            worker_name,
            role=WorkerRole.ANALYST,
            tenant_config=tenant_config,
            autonomy_level=autonomy_level,
            instructions=instructions,
            tools=[toolkit],
            description="Compliance analyst worker",
            tags=["analyst", "compliance"],
            **kwargs,
        )

    @staticmethod
    def _build_instructions(config: TenantConfig) -> str:
        parts: list[str] = [
            "You are a regulatory compliance analyst. Your role is to "
            "review business processes against regulatory requirements, "
            "identify compliance gaps, and recommend remediation actions. "
            "Reference relevant regulations (SOX, GDPR, HIPAA, PCI-DSS) "
            "and maintain audit-ready documentation standards.",
        ]

        # Add vertical fragments
        from firefly_dworkers.verticals import get_vertical
        from firefly_dworkers.exceptions import VerticalNotFoundError

        for v_name in config.verticals:
            try:
                v = get_vertical(v_name)
                parts.append(v.system_prompt_fragment)
            except VerticalNotFoundError:
                pass

        settings = config.workers.settings_for("analyst")
        if settings.custom_instructions:
            parts.append(settings.custom_instructions)

        return "\n\n".join(parts)
```

### Step 3: Import the Module

For the `@worker_factory.register()` decorator to execute, the module must be imported. Add the import to your application's startup code:

```python
from __future__ import annotations

# Import triggers registration
import my_package.workers.compliance_analyst  # noqa: F401
```

### Step 4: Use the Worker

Once registered, the worker is available through the factory:

```python
from __future__ import annotations

from firefly_dworkers.tenants import load_tenant_config
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.factory import worker_factory

config = load_tenant_config("config/tenants/acme-corp.yaml")
worker = worker_factory.create(
    WorkerRole.ANALYST,
    config,
    name="sox-compliance-review",
)
```

---

## Creating a Custom Toolkit

If your worker needs a different set of tools, create a custom toolkit factory:

```python
from __future__ import annotations

from fireflyframework_genai.tools.base import BaseTool
from fireflyframework_genai.tools.toolkit import ToolKit

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.tools.registry import tool_registry


def compliance_toolkit(config: TenantConfig) -> ToolKit:
    """Build a ToolKit for compliance analysis."""
    tools: list[BaseTool] = []

    # Build storage tools from tenant config using the public registry API
    storage_tools = []
    for name in ("sharepoint", "google_drive", "confluence"):
        cfg = getattr(config.connectors, name, None)
        if cfg is not None and getattr(cfg, "enabled", False) and tool_registry.has(name):
            storage_tools.append(tool_registry.create(name))

    # Include storage tools for document access
    tools.extend(storage_tools)

    # Include specific consulting tools
    tools.append(tool_registry.create("requirement_gathering"))
    tools.append(tool_registry.create("gap_analysis"))
    tools.append(tool_registry.create("documentation"))
    tools.append(tool_registry.create("report_generation"))

    return ToolKit(
        f"compliance-{config.id}",
        tools,
        description="Compliance analysis tools",
        tags=["compliance"],
    )
```

Then reference it in your worker:

```python
from __future__ import annotations

class ComplianceAnalystWorker(BaseWorker):
    def __init__(self, tenant_config: TenantConfig, **kwargs: Any) -> None:
        toolkit = compliance_toolkit(tenant_config)
        # ... rest of init
```

---

## Overriding an Existing Role

The default `WorkerFactory` raises `ValueError` if you attempt to register a different class for an already-registered role. To override a built-in role, use a fresh `WorkerFactory` instance or call `clear()` before re-registering:

```python
from __future__ import annotations

from firefly_dworkers.workers.factory import WorkerFactory
from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.types import WorkerRole


# Option A: use a new factory instance
custom_factory = WorkerFactory()

@custom_factory.register(WorkerRole.RESEARCHER)
class EnhancedResearcherWorker(BaseWorker):
    """Custom researcher with additional capabilities."""
    ...

# Option B: clear the singleton and re-register
from firefly_dworkers.workers.factory import worker_factory

worker_factory.clear()

@worker_factory.register(WorkerRole.RESEARCHER)
class EnhancedResearcherWorker(BaseWorker):
    """Custom researcher with additional capabilities."""
    ...
```

Note: calling `clear()` removes **all** registrations, so you must re-register every role you need afterward. Using a separate `WorkerFactory` instance is safer when you only need to override a single role.

---

## Testing Custom Workers

```python
from __future__ import annotations

import pytest

from firefly_dworkers.tenants.config import TenantConfig
from firefly_dworkers.types import WorkerRole
from firefly_dworkers.workers.factory import WorkerFactory


@pytest.fixture
def factory():
    """Provide a clean factory for each test."""
    f = WorkerFactory()
    yield f
    f.clear()


@pytest.fixture
def tenant_config():
    """Minimal tenant config for testing."""
    return TenantConfig(id="test", name="Test Tenant")


def test_custom_worker_registration(factory, tenant_config):
    """Custom worker registers and creates correctly."""
    from my_package.workers.compliance_analyst import ComplianceAnalystWorker

    factory.register(WorkerRole.ANALYST)(ComplianceAnalystWorker)

    assert factory.has(WorkerRole.ANALYST)
    worker = factory.create(WorkerRole.ANALYST, tenant_config, name="test-worker")
    assert worker.role == WorkerRole.ANALYST
    assert "compliance" in worker.name or "test-worker" == worker.name
```

---

## Related Documentation

- [Workers Overview](overview.md) -- Built-in worker roles and lifecycle
- [Tool Registry](../tools/registry.md) -- Creating and registering custom tools
- [Verticals Overview](../verticals/overview.md) -- Adding vertical-specific instructions
