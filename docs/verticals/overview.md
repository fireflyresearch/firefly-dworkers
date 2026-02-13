# Verticals Overview

## Contents

- [Module](#module)
- [Built-in Verticals](#built-in-verticals)
- [VerticalConfig](#verticalconfig)
  - [Example: Banking Vertical](#example-banking-vertical)
- [How Verticals Are Used](#how-verticals-are-used)
- [Configuring Verticals](#configuring-verticals)
- [Vertical Focus Areas by Industry](#vertical-focus-areas-by-industry)
  - [Banking & Financial Services](#banking--financial-services)
  - [Healthcare](#healthcare)
  - [Technology](#technology)
  - [Gaming & Entertainment](#gaming--entertainment)
  - [Legal](#legal)
  - [Consumer Products & Retail](#consumer-products--retail)
- [Creating a Custom Vertical](#creating-a-custom-vertical)
  - [Step 1: Define the VerticalConfig](#step-1-define-the-verticalconfig)
  - [Step 2: Import at Startup](#step-2-import-at-startup)
  - [Step 3: Use in Tenant Config](#step-3-use-in-tenant-config)
- [API](#api)
  - [get_vertical(name)](#get_verticalname)
  - [list_verticals()](#list_verticals)
- [Related Documentation](#related-documentation)

---

Verticals provide industry-specific configuration for digital workers. Each vertical defines domain terminology, focus areas, and system prompt fragments that are injected into worker instructions when the vertical is activated for a tenant.

---

## Module

```
firefly_dworkers.verticals
```

Key components:

| Component | Purpose |
|-----------|---------|
| `VerticalConfig` | Frozen dataclass holding vertical metadata and prompt fragment |
| `register_vertical()` | Function to register a vertical in the module-level registry |
| `get_vertical(name)` | Retrieve a registered vertical by name |
| `list_verticals()` | List all registered vertical names |

---

## Built-in Verticals

firefly-dworkers ships with six industry verticals:

| Name | Display Name | Module |
|------|-------------|--------|
| `banking` | Banking & Financial Services | `firefly_dworkers.verticals.banking` |
| `healthcare` | Healthcare | `firefly_dworkers.verticals.healthcare` |
| `technology` | Technology | `firefly_dworkers.verticals.technology` |
| `gaming` | Gaming & Entertainment | `firefly_dworkers.verticals.gaming` |
| `legal` | Legal | `firefly_dworkers.verticals.legal` |
| `consumer` | Consumer Products & Retail | `firefly_dworkers.verticals.consumer` |

---

## VerticalConfig

Each vertical is defined as a frozen dataclass:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerticalConfig:
    name: str                          # Unique identifier (e.g., "banking")
    display_name: str                  # Human-readable name
    focus_areas: list[str]             # Key consulting focus areas
    system_prompt_fragment: str        # Text injected into worker instructions
    keywords: list[str] = field(default_factory=list)  # Domain keywords
```

### Example: Banking Vertical

```python
from __future__ import annotations

from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

BANKING = VerticalConfig(
    name="banking",
    display_name="Banking & Financial Services",
    focus_areas=[
        "Financial strategy and planning",
        "Regulatory compliance (Basel III, PSD2)",
        "Fraud detection and prevention",
        "Risk management and assessment",
        "Fintech integration and innovation",
    ],
    system_prompt_fragment=(
        "You are working in the Banking & Financial Services consulting vertical. "
        "Focus on financial strategy, regulatory compliance, fraud detection, "
        "risk management, and fintech integration. Reference frameworks like "
        "Basel III, PSD2, AML/KYC requirements, and IFRS standards. Use "
        "terminology appropriate for banking executives (CFO, CRO, Head of "
        "Compliance) and maintain awareness of evolving financial regulations."
    ),
    keywords=[
        "Basel III", "PSD2", "AML", "KYC",
        "risk management", "fintech", "fraud detection",
    ],
)
register_vertical(BANKING)
```

---

## How Verticals Are Used

When a worker is created, its `_build_instructions()` method iterates over the tenant's `verticals` list and appends each vertical's `system_prompt_fragment` to the system prompt:

```python
from __future__ import annotations

# Inside a worker's _build_instructions() method:
for v_name in config.verticals:
    try:
        v = get_vertical(v_name)
        parts.append(v.system_prompt_fragment)
    except VerticalNotFoundError:
        logger.debug("Skipping unknown vertical '%s'", v_name)
```

For a tenant with `verticals: [banking, technology]`, the worker's system prompt would include both the banking and technology fragments, in addition to the role-specific base prompt and any custom instructions.

---

## Configuring Verticals

Activate verticals in the tenant YAML:

```yaml
id: acme-corp
name: Acme Corporation

verticals:
  - banking
  - technology
```

Multiple verticals can be activated simultaneously. They are applied in order, with each fragment appended as a separate paragraph.

---

## Vertical Focus Areas by Industry

### Banking & Financial Services

- Financial strategy and planning
- Regulatory compliance (Basel III, PSD2)
- Fraud detection and prevention
- Risk management and assessment
- Fintech integration and innovation

### Healthcare

- Strategy and policy consulting
- Patient data analysis and outcomes
- Operational efficiency and workflow optimization
- Regulatory compliance (HIPAA, FDA)
- Clinical workflow improvement

### Technology

- Strategic IT planning
- Technology adoption and digital transformation
- Data-driven decision support
- Cloud architecture and migration
- Cybersecurity strategy

### Gaming & Entertainment

- Market entry and competitive analysis
- Consumer behavior and player analytics
- User engagement and retention strategy
- Monetization strategy and optimization
- Content strategy and IP development

### Legal

- Legal compliance and governance
- Contract management and analysis
- Regulatory research and monitoring
- Intellectual property strategy
- Litigation support and case analysis

### Consumer Products & Retail

- Market entry and growth strategy
- Consumer behavior and trend analysis
- Brand management and positioning
- Retail strategy and channel optimization
- E-commerce and direct-to-consumer

---

## Creating a Custom Vertical

### Step 1: Define the VerticalConfig

```python
# my_package/verticals/energy.py
from __future__ import annotations

from firefly_dworkers.verticals.base import VerticalConfig, register_vertical

ENERGY = VerticalConfig(
    name="energy",
    display_name="Energy & Utilities",
    focus_areas=[
        "Renewable energy transition strategy",
        "Grid modernization and smart infrastructure",
        "Regulatory compliance (FERC, NERC)",
        "Carbon reduction and sustainability",
        "Energy trading and market optimization",
    ],
    system_prompt_fragment=(
        "You are working in the Energy & Utilities consulting vertical. "
        "Focus on renewable energy transition, grid modernization, regulatory "
        "compliance, carbon reduction strategies, and energy market optimization. "
        "Reference industry frameworks (FERC, NERC, ISO 50001) and use "
        "terminology appropriate for energy executives (CEO, VP Operations, "
        "Chief Sustainability Officer)."
    ),
    keywords=[
        "renewable energy", "grid modernization", "FERC", "NERC",
        "carbon reduction", "sustainability", "energy trading",
    ],
)
register_vertical(ENERGY)
```

### Step 2: Import at Startup

```python
from __future__ import annotations

import my_package.verticals.energy  # noqa: F401
```

### Step 3: Use in Tenant Config

```yaml
verticals:
  - energy
  - technology
```

---

## API

### get_vertical(name)

Retrieve a vertical by name. Raises `VerticalNotFoundError` if not found.

```python
from __future__ import annotations

from firefly_dworkers.verticals import get_vertical

v = get_vertical("banking")
print(v.display_name)  # "Banking & Financial Services"
print(v.focus_areas)   # ["Financial strategy and planning", ...]
```

### list_verticals()

List all registered vertical names (sorted alphabetically).

```python
from __future__ import annotations

from firefly_dworkers.verticals import list_verticals

names = list_verticals()
# ["banking", "consumer", "gaming", "healthcare", "legal", "technology"]
```

---

## Related Documentation

- [Workers Overview](../workers/overview.md) -- How workers use vertical fragments
- [Configuration](../configuration.md) -- Tenant YAML vertical configuration
- [Custom Workers](../workers/custom-workers.md) -- Using verticals in custom workers
