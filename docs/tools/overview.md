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
  - [Presentation](#presentation)
  - [Document](#document)
  - [Spreadsheet](#spreadsheet)
  - [Vision](#vision)
- [Port / Adapter Pattern](#port--adapter-pattern)
  - [WebSearchTool](#websearchtool)
  - [WebBrowsingTool](#webbrowsingtool)
  - [DocumentStorageTool](#documentstoragetool)
  - [MessageTool](#messagetool)
  - [ProjectManagementTool](#projectmanagementtool)
  - [ConsultingTool](#consultingtool)
  - [PresentationTool](#presentationtool)
  - [DocumentTool](#documenttool)
  - [SpreadsheetPort](#spreadsheetport)
- [Data Models](#data-models)
- [Toolkits](#toolkits)
- [Tool Resilience](#tool-resilience)
- [Optional Dependencies](#optional-dependencies)
- [Related Documentation](#related-documentation)

---

The tool system in firefly-dworkers provides pluggable connectors that digital workers use to interact with external services. It follows a hexagonal architecture with abstract ports, concrete adapters, and a decorator-based registry for self-registration.

---

## Tool Categories

Tools are organized into eleven categories:

| Category | Port (Abstract Base) | Module | Purpose |
|----------|---------------------|--------|---------|
| Web Search | `WebSearchTool` | `firefly_dworkers.tools.web.search` | Internet search via external providers |
| Web | `WebBrowsingTool` | `firefly_dworkers.tools.web.browsing` | Web page navigation and content extraction |
| Storage | `DocumentStorageTool` | `firefly_dworkers.tools.storage.base` | Document access (read, write, search, list) |
| Communication | `MessageTool` | `firefly_dworkers.tools.communication.base` | Messaging (send, read, list channels) |
| Project | `ProjectManagementTool` | `firefly_dworkers.tools.project.base` | Task management (create, list, update, get) |
| Data | -- | `firefly_dworkers.tools.data` | API and database access |
| Consulting | `ConsultingTool` | `firefly_dworkers.tools.consulting.base` | Domain-specific consulting operations |
| Presentation | `PresentationTool` | `firefly_dworkers.tools.presentation.base` | Slide deck creation and management |
| Document | `DocumentTool` | `firefly_dworkers.tools.document.base` | Document creation and section management |
| Spreadsheet | `SpreadsheetPort` | `firefly_dworkers.tools.spreadsheet.base` | Spreadsheet creation, reading, and management |
| Vision | -- | `firefly_dworkers.tools.vision` | Image and visual content analysis |

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
| `SQLTool` | `sql` | `firefly_dworkers.tools.data.sql` | (driver-dependent) |
| `APIClientTool` | `api_client` | `firefly_dworkers.tools.data.api_client` | httpx |

### Presentation

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `PowerPointTool` | `powerpoint` | `firefly_dworkers.tools.presentation.powerpoint` | python-pptx |
| `GoogleSlidesTool` | `google_slides` | `firefly_dworkers.tools.presentation.google_slides` | google-api-python-client |

### Document

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `WordTool` | `word` | `firefly_dworkers.tools.document.word` | python-docx |
| `GoogleDocsTool` | `google_docs` | `firefly_dworkers.tools.document.google_docs` | google-api-python-client |
| `PDFTool` | `pdf` | `firefly_dworkers.tools.document.pdf` | weasyprint |

### Spreadsheet

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `ExcelTool` | `excel` | `firefly_dworkers.tools.spreadsheet.excel` | openpyxl |
| `GoogleSheetsTool` | `google_sheets_spreadsheet` | `firefly_dworkers.tools.spreadsheet.google_sheets` | google-api-python-client |

### Vision

| Adapter | Registry Key | Module | Dependencies |
|---------|-------------|--------|--------------|
| `VisionAnalysisTool` | `vision_analysis` | `firefly_dworkers.tools.vision.analysis` | (none -- uses LLM) |

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

### PresentationTool

**Module:** `firefly_dworkers.tools.presentation.base`

**Abstract methods:**

```python
@abstractmethod
async def _read_presentation(self, source: str) -> PresentationData: ...

@abstractmethod
async def _create_presentation(self, template: str, slides: list[SlideSpec]) -> bytes: ...

@abstractmethod
async def _modify_presentation(self, source: str, operations: list[SlideOperation]) -> bytes: ...
```

**Public convenience methods:**

```python
tool.artifact_bytes          # bytes | None — last create/modify result
await tool.create(slides=[...])                         # → bytes
await tool.create_and_save("out.pptx", slides=[...])    # → str (absolute path)
await tool.modify("src.pptx", operations=[...])         # → bytes
await tool.modify_and_save("src.pptx", "out.pptx", operations=[...])  # → str
```

**Adapters:** `PowerPointTool`, `GoogleSlidesTool`

### DocumentTool

**Module:** `firefly_dworkers.tools.document.base`

**Abstract methods:**

```python
@abstractmethod
async def _read_document(self, source: str) -> DocumentData: ...

@abstractmethod
async def _create_document(self, title: str, sections: list[SectionSpec]) -> bytes: ...

@abstractmethod
async def _modify_document(self, source: str, operations: list[DocumentOperation]) -> bytes: ...
```

**Public convenience methods:**

```python
tool.artifact_bytes          # bytes | None — last create/modify result
await tool.create(title="...", sections=[...])                    # → bytes
await tool.create_and_save("out.docx", title="...", sections=[...])  # → str
await tool.modify("src.docx", operations=[...])                  # → bytes
await tool.modify_and_save("src.docx", "out.docx", operations=[...])  # → str
```

**Adapters:** `WordTool`, `GoogleDocsTool`, `PDFTool`

### SpreadsheetPort

**Module:** `firefly_dworkers.tools.spreadsheet.base`

**Abstract methods:**

```python
@abstractmethod
async def _read_spreadsheet(self, source: str, sheet_name: str = "") -> WorkbookData: ...

@abstractmethod
async def _create_spreadsheet(self, sheets: list[SheetSpec]) -> bytes: ...

@abstractmethod
async def _modify_spreadsheet(self, source: str, operations: list[SpreadsheetOperation]) -> bytes: ...
```

**Public convenience methods:**

```python
tool.artifact_bytes          # bytes | None — last create/modify result
await tool.create(sheets=[...])                                     # → bytes
await tool.create_and_save("out.xlsx", sheets=[...])                # → str
await tool.modify("src.xlsx", operations=[...])                     # → bytes
await tool.modify_and_save("src.xlsx", "out.xlsx", operations=[...])  # → str
```

**Adapters:** `ExcelTool`, `GoogleSheetsTool`

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
| `SlideData` | `PresentationTool` | `title`, `content`, `layout`, `notes` |
| `DocumentSection` | `DocumentTool` | `heading`, `content`, `level` |
| `SheetData` | `SpreadsheetPort` | `name`, `headers`, `rows` |

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

## Tool Resilience

The toolkit factories use framework composition patterns for resilient tool chains:

**FallbackComposer** wraps the primary web search provider with alternatives. If Tavily fails, SerpAPI is tried automatically:

```python
from __future__ import annotations

from fireflyframework_genai.tools import FallbackComposer

composer = FallbackComposer(
    "web_search",
    tools=[primary_search, fallback_search],
    description="Resilient web search with fallbacks",
)
```

**SequentialComposer** chains tools where output flows from one to the next. The researcher toolkit uses this for automated research workflows:

```python
from __future__ import annotations

from fireflyframework_genai.tools import SequentialComposer

chain = SequentialComposer(
    "research_chain",
    tools=[web_search, report_generation],
    description="Search web then generate report",
)
```

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
            "httpx required for TavilySearchTool -- "
            "reinstall dworkers with the 'web' extra enabled"
        )
    ...
```

---

## Design Intelligence Layer

The `design/` package provides LLM-powered creative reasoning for document generation.

### DesignEngine

**Module:** `firefly_dworkers.design.engine`

Takes a `ContentBrief` and optional `DesignProfile`, uses an LLM to produce a complete `DesignSpec`.

### TemplateAnalyzer

**Module:** `firefly_dworkers.design.analyzer`

Extracts design DNA (colors, fonts, layouts) from existing documents (PPTX, DOCX, XLSX).

### ChartRenderer

**Module:** `firefly_dworkers.design.charts`

Renders charts as native objects (PPTX, XLSX) or PNG images (DOCX, PDF).

---

## Related Documentation

- [Tool Registry](registry.md) -- Creating and registering custom tools
- [Workers Overview](../workers/overview.md) -- How workers use tools
- [Configuration](../configuration.md) -- Connector configuration reference
