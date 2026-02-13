# Tool Registry

## Contents

- [Module](#module)
- [How Registration Works](#how-registration-works)
  - [Triggering Registration](#triggering-registration)
- [API Reference](#api-reference)
  - [register(name, category)](#registername-category)
  - [create(name, **kwargs)](#createname-kwargs)
  - [get_class(name)](#get_classname)
  - [has(name)](#hasname)
  - [list_tools()](#list_tools)
  - [list_by_category(category)](#list_by_categorycategory)
  - [get_category(name)](#get_categoryname)
  - [clear()](#clear)
- [Creating a Custom Tool](#creating-a-custom-tool)
  - [Step 1: Choose or Create a Port](#step-1-choose-or-create-a-port)
  - [Step 2: Implement the Tool](#step-2-implement-the-tool)
  - [Step 3: Register via Import](#step-3-register-via-import)
  - [Step 4: Use in a Toolkit](#step-4-use-in-a-toolkit)
- [Thread Safety](#thread-safety)
- [Categories](#categories)
- [Related Documentation](#related-documentation)

---

The `ToolRegistry` is the central mechanism for tool discovery and creation in firefly-dworkers. It uses a decorator-based pattern that allows tools to self-register at import time.

---

## Module

```
firefly_dworkers.tools.registry
```

The module provides:

- `ToolRegistry` -- The registry class
- `tool_registry` -- A module-level singleton instance

---

## How Registration Works

Tools register themselves using the `@tool_registry.register()` decorator:

```python
from __future__ import annotations

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.web.search import WebSearchTool


@tool_registry.register("tavily", category="web_search")
class TavilySearchTool(WebSearchTool):
    """Web search using the Tavily API."""

    def __init__(self, *, api_key: str, **kwargs):
        ...
```

When this module is imported, the decorator stores the class in the registry under the key `"tavily"` with category `"web_search"`.

### Triggering Registration

All concrete tool modules are imported in `firefly_dworkers.tools.__init__`, which triggers all decorators:

```python
from __future__ import annotations

# Web Search
import firefly_dworkers.tools.web.tavily            # registers "tavily"
import firefly_dworkers.tools.web.serpapi            # registers "serpapi"

# Web
import firefly_dworkers.tools.web.browser            # registers "web_browser"
import firefly_dworkers.tools.web.flybrowser          # registers "flybrowser"
import firefly_dworkers.tools.web.rss                 # registers "rss_feed"

# Storage
import firefly_dworkers.tools.storage.sharepoint      # registers "sharepoint"
import firefly_dworkers.tools.storage.google_drive     # registers "google_drive"
import firefly_dworkers.tools.storage.confluence       # registers "confluence"
import firefly_dworkers.tools.storage.s3               # registers "s3"

# Communication
import firefly_dworkers.tools.communication.slack      # registers "slack"
import firefly_dworkers.tools.communication.teams      # registers "teams"
import firefly_dworkers.tools.communication.email      # registers "email"

# Project
import firefly_dworkers.tools.project.jira             # registers "jira"
import firefly_dworkers.tools.project.asana            # registers "asana"

# Data
import firefly_dworkers.tools.data.csv_excel           # registers "spreadsheet"
import firefly_dworkers.tools.data.api_client          # registers "api_client"
import firefly_dworkers.tools.data.sql                 # registers "sql"

# Consulting
import firefly_dworkers.tools.consulting.report_generation       # registers "report_generation"
import firefly_dworkers.tools.consulting.requirement_gathering   # registers "requirement_gathering"
import firefly_dworkers.tools.consulting.process_mapping         # registers "process_mapping"
import firefly_dworkers.tools.consulting.gap_analysis            # registers "gap_analysis"
import firefly_dworkers.tools.consulting.documentation           # registers "documentation"
```

---

## API Reference

### register(name, category)

Decorator that registers a tool class under the given name and category.

```python
from __future__ import annotations

@tool_registry.register("my_tool", category="custom")
class MyTool(BaseTool):
    ...
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | (required) | Unique key for the tool |
| `category` | `str` | `"general"` | Logical grouping label |

**Raises:** `ValueError` if `name` is already registered to a *different* class.

Re-registering the same class under the same name is a no-op (idempotent).

### create(name, **kwargs)

Instantiate a registered tool by name.

```python
from __future__ import annotations

tool = tool_registry.create("tavily", api_key="tvly-...")
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Registered tool key |
| `**kwargs` | `Any` | Passed to the tool's constructor |

**Raises:** `KeyError` if the name is not registered.

### get_class(name)

Return the raw class without instantiating.

```python
from __future__ import annotations

cls = tool_registry.get_class("tavily")
# cls is TavilySearchTool
```

**Returns:** `type` -- the registered tool class.

**Raises:** `KeyError` if the name is not registered.

### has(name)

Check if a tool is registered.

```python
from __future__ import annotations

if tool_registry.has("tavily"):
    tool = tool_registry.create("tavily", api_key="...")
```

**Returns:** `bool`

### list_tools()

Return all registered tool names.

```python
from __future__ import annotations

names = tool_registry.list_tools()
# ["tavily", "serpapi", "web_browser", "flybrowser", "rss_feed",
#  "sharepoint", "google_drive", "confluence", "s3",
#  "slack", "teams", "email", "jira", "asana",
#  "spreadsheet", "api_client", "sql",
#  "report_generation", "requirement_gathering",
#  "process_mapping", "gap_analysis", "documentation"]
```

**Returns:** `list[str]`

### list_by_category(category)

Return tool names filtered by category.

```python
from __future__ import annotations

web_search_tools = tool_registry.list_by_category("web_search")
# ["tavily", "serpapi"]

web_tools = tool_registry.list_by_category("web")
# ["web_browser", "flybrowser", "rss_feed"]

storage_tools = tool_registry.list_by_category("storage")
# ["sharepoint", "google_drive", "confluence", "s3"]

communication_tools = tool_registry.list_by_category("communication")
# ["slack", "teams", "email"]

project_tools = tool_registry.list_by_category("project")
# ["jira", "asana"]

data_tools = tool_registry.list_by_category("data")
# ["spreadsheet", "api_client", "sql"]

consulting_tools = tool_registry.list_by_category("consulting")
# ["report_generation", "requirement_gathering", "process_mapping",
#  "gap_analysis", "documentation"]
```

**Returns:** `list[str]`

### get_category(name)

Return the category of a registered tool.

```python
from __future__ import annotations

category = tool_registry.get_category("tavily")
# "web_search"

category = tool_registry.get_category("flybrowser")
# "web"
```

**Returns:** `str`

**Raises:** `KeyError` if the name is not registered.

### clear()

Remove all registrations. Primarily used in testing.

```python
from __future__ import annotations

tool_registry.clear()
assert tool_registry.list_tools() == []
```

---

## Creating a Custom Tool

### Step 1: Choose or Create a Port

If your tool fits an existing category, extend the appropriate port:

```python
from __future__ import annotations

from firefly_dworkers.tools.web.search import WebSearchTool, SearchResult
```

If it is a new category, extend `BaseTool` directly:

```python
from __future__ import annotations

from fireflyframework_genai.tools.base import BaseTool, ParameterSpec
```

### Step 2: Implement the Tool

```python
from __future__ import annotations

from typing import Any

from fireflyframework_genai.tools.base import BaseTool, ParameterSpec
from firefly_dworkers.tools.registry import tool_registry


@tool_registry.register("sentiment_analysis", category="analytics")
class SentimentAnalysisTool(BaseTool):
    """Analyze sentiment of text content."""

    def __init__(self, *, model_name: str = "default", **kwargs: Any):
        super().__init__(
            "sentiment_analysis",
            description="Analyze the sentiment of text content",
            tags=["analytics", "nlp", "sentiment"],
            parameters=[
                ParameterSpec(
                    name="text",
                    type_annotation="str",
                    description="Text to analyze",
                    required=True,
                ),
                ParameterSpec(
                    name="granularity",
                    type_annotation="str",
                    description="Analysis granularity: document, paragraph, or sentence",
                    required=False,
                    default="document",
                ),
            ],
        )
        self._model_name = model_name

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        text = kwargs["text"]
        granularity = kwargs.get("granularity", "document")

        # Your implementation here
        return {
            "sentiment": "positive",
            "confidence": 0.87,
            "granularity": granularity,
        }
```

### Step 3: Register via Import

Ensure the module is imported at startup:

```python
from __future__ import annotations

# In your application's startup or __init__.py
import my_package.tools.sentiment_analysis  # noqa: F401
```

### Step 4: Use in a Toolkit

```python
from __future__ import annotations

from firefly_dworkers.tools.registry import tool_registry

tool = tool_registry.create("sentiment_analysis", model_name="advanced")
```

---

## Thread Safety

`ToolRegistry` uses `threading.Lock` for all operations, making it safe to use in concurrent environments.

---

## Categories

The built-in categories are:

| Category | Tools |
|----------|-------|
| `web_search` | tavily, serpapi |
| `web` | web_browser, flybrowser, rss_feed |
| `storage` | sharepoint, google_drive, confluence, s3 |
| `communication` | slack, teams, email |
| `project` | jira, asana |
| `consulting` | report_generation, process_mapping, gap_analysis, requirement_gathering, documentation |
| `data` | spreadsheet, sql, api_client |

---

## Related Documentation

- [Tools Overview](overview.md) -- Port/adapter pattern and built-in tools
- [Custom Workers](../workers/custom-workers.md) -- Using custom tools in workers
- [Configuration](../configuration.md) -- Connector configuration for built-in tools
