# Tools Overview

## Contents

- [Tool Categories](#tool-categories)
- [Built-in Adapters](#built-in-adapters)
  - [Web Search](#web-search)
  - [Web](#web)
  - [Storage](#storage)
  - [Communication](#communication)
  - [Project Management](#project-management)
  - [Consulting](#consulting)
  - [Data](#data)
- [Port / Adapter Pattern](#port--adapter-pattern)
  - [WebSearchTool](#websearchtool)
  - [WebBrowsingTool](#webbrowsingtool)
  - [DocumentStorageTool](#documentstoragetool)
  - [MessageTool](#messagetool)
  - [ProjectManagementTool](#projectmanagementtool)
  - [ConsultingTool](#consultingtool)
- [Data Models](#data-models)
- [Toolkits](#toolkits)
- [Optional Dependencies](#optional-dependencies)
- [Related Documentation](#related-documentation)

---

The tool system in firefly-dworkers provides pluggable connectors that digital workers use to interact with external services. It follows a hexagonal architecture with abstract ports, concrete adapters, and a decorator-based registry for self-registration.

---

## Tool Categories

Tools are organized into seven categories:

| Category | Port (Abstract Base) | Module | Purpose |
|----------|---------------------|--------|---------|
| Web Search | `WebSearchTool` | `firefly_dworkers.tools.web.search` | Internet search via external providers |
| Web | `WebBrowsingTool` | `firefly_dworkers.tools.web.browsing` | Web page navigation and content extraction |
| Storage | `DocumentStorageTool` | `firefly_dworkers.tools.storage.base` | Document access (read, write, search, list) |
| Communication | `MessageTool` | `firefly_dworkers.tools.communication.base` | Messaging (send, read, list channels) |
| Project | `ProjectManagementTool` | `firefly_dworkers.tools.project.base` | Task management (create, list, update, get) |
| Data | -- | `firefly_dworkers.tools.data` | Spreadsheet, API, and database access |
| Consulting | `ConsultingTool` | `firefly_dworkers.tools.consulting.base` | Domain-specific consulting operations |

---

## Built-in Adapters

### Web Search

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `TavilySearchTool` | `tavily` | `firefly_dworkers.tools.web.tavily` | httpx |
| `SerpAPISearchTool` | `serpapi` | `firefly_dworkers.tools.web.serpapi` | httpx |

### Web

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `WebBrowserTool` | `web_browser` | `firefly_dworkers.tools.web.browser` | httpx, beautifulsoup4 |
| `FlyBrowserTool` | `flybrowser` | `firefly_dworkers.tools.web.flybrowser` | flybrowser, playwright |
| `RSSFeedTool` | `rss_feed` | `firefly_dworkers.tools.web.rss` | feedparser |

### Storage

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `SharePointTool` | `sharepoint` | `firefly_dworkers.tools.storage.sharepoint` | msal, httpx |
| `GoogleDriveTool` | `google_drive` | `firefly_dworkers.tools.storage.google_drive` | google-api-python-client |
| `ConfluenceTool` | `confluence` | `firefly_dworkers.tools.storage.confluence` | atlassian-python-api |
| `S3Tool` | `s3` | `firefly_dworkers.tools.storage.s3` | boto3 |

### Communication

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `SlackTool` | `slack` | `firefly_dworkers.tools.communication.slack` | slack-sdk |
| `TeamsTool` | `teams` | `firefly_dworkers.tools.communication.teams` | msgraph-sdk |
| `EmailTool` | `email` | `firefly_dworkers.tools.communication.email` | aiosmtplib |

### Project Management

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `JiraTool` | `jira` | `firefly_dworkers.tools.project.jira` | atlassian-python-api |
| `AsanaTool` | `asana` | `firefly_dworkers.tools.project.asana` | httpx |

### Consulting

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `ReportGenerationTool` | `report_generation` | `firefly_dworkers.tools.consulting.report_generation` | (none) |
| `ProcessMappingTool` | `process_mapping` | `firefly_dworkers.tools.consulting.process_mapping` | (none) |
| `GapAnalysisTool` | `gap_analysis` | `firefly_dworkers.tools.consulting.gap_analysis` | (none) |
| `RequirementGatheringTool` | `requirement_gathering` | `firefly_dworkers.tools.consulting.requirement_gathering` | (none) |
| `DocumentationTool` | `documentation` | `firefly_dworkers.tools.consulting.documentation` | (none) |

### Data

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `SpreadsheetTool` | `spreadsheet` | `firefly_dworkers.tools.data.csv_excel` | openpyxl (for Excel) |
| `SQLTool` | `sql` | `firefly_dworkers.tools.data.sql` | (driver-dependent) |
| `APIClientTool` | `api_client` | `firefly_dworkers.tools.data.api_client` | httpx |

---

## Port / Adapter Pattern

Each tool category defines an abstract base class (port) with abstract methods that concrete adapters must implement:

### WebSearchTool

**Module:** `firefly_dworkers.tools.web.search`

**Abstract method:**

```python
@abstractmethod
async def _search(self, query: str, max_results: int) -> list[SearchResult]: ...
```

**Adapters:** `TavilySearchTool`, `SerpAPISearchTool`

### WebBrowsingTool

**Module:** `firefly_dworkers.tools.web.browsing`

Defines the contract for web browsing tools that navigate to URLs and return page content.

**Abstract method:**

```python
@abstractmethod
async def _fetch_page(self, url: str, *, extract_links: bool = False) -> BrowsingResult: ...
```

**Adapters:** `WebBrowserTool` (HTTP + BeautifulSoup), `FlyBrowserTool` (AI-driven via flybrowser)

### DocumentStorageTool

**Module:** `firefly_dworkers.tools.storage.base`

**Abstract methods:**

```python
@abstractmethod
async def _search(self, query: str) -> list[DocumentResult]: ...

@abstractmethod
async def _read(self, resource_id: str, path: str) -> DocumentResult: ...

@abstractmethod
async def _list(self, path: str) -> list[DocumentResult]: ...

@abstractmethod
async def _write(self, path: str, content: str) -> DocumentResult: ...
```

**Adapters:** `SharePointTool`, `GoogleDriveTool`, `ConfluenceTool`, `S3Tool`

### MessageTool

**Module:** `firefly_dworkers.tools.communication.base`

**Abstract methods:**

```python
@abstractmethod
async def _send(self, channel: str, content: str) -> Message: ...

@abstractmethod
async def _read(self, channel: str, message_id: str) -> list[Message]: ...

@abstractmethod
async def _list_channels(self) -> list[str]: ...
```

**Adapters:** `SlackTool`, `TeamsTool`, `EmailTool`

### ProjectManagementTool

**Module:** `firefly_dworkers.tools.project.base`

**Abstract methods:**

```python
@abstractmethod
async def _create_task(self, title: str, description: str, project: str) -> ProjectTask: ...

@abstractmethod
async def _list_tasks(self, project: str) -> list[ProjectTask]: ...

@abstractmethod
async def _update_task(self, task_id: str, status: str) -> ProjectTask: ...

@abstractmethod
async def _get_task(self, task_id: str) -> ProjectTask: ...
```

**Adapters:** `JiraTool`, `AsanaTool`

### ConsultingTool

**Module:** `firefly_dworkers.tools.consulting.base`

`ConsultingTool` extends `BaseTool` and serves as the shared base for all consulting-domain tools. It does not define abstract methods itself; instead, each consulting adapter implements `_execute` directly. The base class ensures all consulting tools share the `"consulting"` tag.

```python
class ConsultingTool(BaseTool):
    """Abstract base for consulting-domain tools.

    Ensures all consulting tools share the 'consulting' tag and
    provides a consistent constructor pattern.  Subclasses implement
    _execute as with any BaseTool.
    """
```

**Adapters:** `ReportGenerationTool`, `RequirementGatheringTool`, `ProcessMappingTool`, `GapAnalysisTool`, `DocumentationTool`

---

## Data Models

Each port defines Pydantic models for its return types:

| Model | Port | Fields |
|-------|------|--------|
| `SearchResult` | `WebSearchTool` | `title`, `url`, `snippet` |
| `BrowsingResult` | `WebBrowsingTool` | `url`, `text`, `status_code`, `title`, `links`, `metadata` |
| `DocumentResult` | `DocumentStorageTool` | `id`, `name`, `path`, `content`, `content_type`, `size_bytes`, `modified_at`, `url` |
| `Message` | `MessageTool` | `id`, `channel`, `sender`, `content`, `timestamp` |
| `ProjectTask` | `ProjectManagementTool` | `id`, `title`, `description`, `status`, `assignee`, `priority`, `project` |

---

## Toolkits

Toolkits bundle tools together for a specific worker role. The toolkit factory functions in `firefly_dworkers.tools.toolkits` assemble tools based on tenant configuration:

```python
from __future__ import annotations

from firefly_dworkers.tools.toolkits import researcher_toolkit
from firefly_dworkers.tenants import load_tenant_config

config = load_tenant_config("config/tenants/acme-corp.yaml")
toolkit = researcher_toolkit(config)
```

Each toolkit function:

1. Reads the tenant's `connectors` config to determine which providers are enabled.
2. Creates tool instances from the `ToolRegistry` for enabled connectors.
3. Bundles them into a `ToolKit` instance tagged for the worker role.

---

## Optional Dependencies

Tools with external dependencies use optional imports and raise clear errors when dependencies are missing:

```python
from __future__ import annotations

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None
    HTTPX_AVAILABLE = False

# In the tool method:
async def _search(self, query: str, max_results: int) -> list[SearchResult]:
    if not HTTPX_AVAILABLE:
        raise ImportError(
            "httpx required for TavilySearchTool -- install with: "
            "pip install firefly-dworkers[web]"
        )
    ...
```

---

## Related Documentation

- [Tool Registry](registry.md) -- Creating and registering custom tools
- [Workers Overview](../workers/overview.md) -- How workers use tools
- [Configuration](../configuration.md) -- Connector configuration reference
