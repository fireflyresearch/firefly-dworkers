# Contributing Guide

## Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
  - [Clone the Repository](#clone-the-repository)
  - [Install Dependencies](#install-dependencies)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
  - [All Tests](#all-tests)
  - [With Coverage](#with-coverage)
  - [Specific Tests](#specific-tests)
  - [Async Tests](#async-tests)
- [Code Quality](#code-quality)
  - [Linting](#linting)
  - [Formatting](#formatting)
  - [Type Checking](#type-checking)
- [Code Style Conventions](#code-style-conventions)
  - [Imports](#imports)
  - [Type Hints](#type-hints)
  - [Thread Safety](#thread-safety)
  - [Naming](#naming)
- [Adding a New Tool](#adding-a-new-tool)
- [Adding a New Worker](#adding-a-new-worker)
- [Adding a New Plan Template](#adding-a-new-plan-template)
- [Adding a New Vertical](#adding-a-new-vertical)
- [Build System](#build-system)
- [Test Organization](#test-organization)
  - [Writing Tests](#writing-tests)
- [Commit Guidelines](#commit-guidelines)
- [Related Documentation](#related-documentation)

---

This guide covers the development workflow for contributing to firefly-dworkers.

---

## Prerequisites

- Python 3.13 or later
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- Git

---

## Development Setup

### Clone the Repository

```bash
git clone https://github.com/fireflyresearch/firefly-dworkers.git
cd firefly-dworkers
```

### Install Dependencies

With uv (recommended):

```bash
uv sync --all-extras
```

With pip:

```bash
pip install -e ".[dev,all]"
```

This installs the package in editable mode with all optional dependencies and development tools.

---

## Project Structure

The repository contains three Python packages in `src/`:

| Package | Purpose | Key Entry Points |
|---------|---------|-----------------|
| `firefly_dworkers` | Core library -- workers, tools, plans, tenants, knowledge, SDK | `from firefly_dworkers import ...` |
| `firefly_dworkers_server` | FastAPI application server | `create_dworkers_app()` |
| `firefly_dworkers_cli` | Typer CLI application | `dworkers` command |

Key source directories inside `firefly_dworkers`:

| Directory | Contents |
|-----------|----------|
| `workers/` | `BaseWorker`, `WorkerFactory`, `WorkerRegistry`, and four role implementations |
| `tools/` | `ToolRegistry`, `toolkits.py`, and six sub-packages (`web/`, `storage/`, `communication/`, `project/`, `consulting/`, `data/`) |
| `plans/` | `BasePlan`, `PlanBuilder`, `PlanRegistry`, and four built-in templates |
| `tenants/` | `TenantConfig`, `TenantLoader`, `TenantRegistry`, `ContextVar`-based per-request context |
| `knowledge/` | `KnowledgeBackend` protocol, `InMemoryKnowledgeBackend`, `KnowledgeRepository`, indexer, retriever |
| `verticals/` | `VerticalConfig` base and six industry verticals |
| `autonomy/` | `CheckpointStore`, autonomy levels, reviewer |
| `sdk/` | `DworkersClient`, `AsyncDworkersClient`, request/response models |

Tests are in the `tests/` directory, mirroring the source structure.

---

## Running Tests

### All Tests

```bash
uv run pytest tests/ -v
```

### With Coverage

```bash
uv run pytest tests/ --cov=firefly_dworkers --cov=firefly_dworkers_server --cov-report=term-missing
```

### Specific Tests

```bash
# Run a specific test file
uv run pytest tests/test_workers/test_factory.py -v

# Run a specific test function
uv run pytest tests/test_workers/test_factory.py::test_factory_create -v

# Run tests matching a pattern
uv run pytest tests/ -k "test_plan" -v
```

### Async Tests

The project uses `pytest-asyncio` with `asyncio_mode = "auto"` configured in `pyproject.toml`. Async test functions are detected and executed automatically:

```python
from __future__ import annotations

async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

---

## Code Quality

### Linting

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting with the following rule sets enabled:

- `E` -- pycodestyle errors
- `F` -- pyflakes
- `W` -- pycodestyle warnings
- `I` -- isort
- `N` -- pep8-naming
- `UP` -- pyupgrade
- `B` -- flake8-bugbear
- `SIM` -- flake8-simplify
- `TC` -- flake8-type-checking

```bash
# Check for lint errors
uv run ruff check src/ tests/

# Auto-fix where possible
uv run ruff check src/ tests/ --fix
```

### Formatting

```bash
# Check formatting
uv run ruff format src/ tests/ --check

# Apply formatting
uv run ruff format src/ tests/
```

Configuration:

- Target version: Python 3.13
- Line length: 120 characters

### Type Checking

The project uses [Pyright](https://github.com/microsoft/pyright) for type checking:

```bash
uv run pyright
```

Configuration:

- Python version: 3.13
- Type checking mode: basic
- Include: `src/`
- Exclude: `tests/`

---

## Code Style Conventions

### Imports

- Always use `from __future__ import annotations` as the first import in every module.
- Use absolute imports for cross-package references.
- Group imports in the standard order: stdlib, third-party, first-party.
- `isort` ordering is enforced by Ruff with `known-first-party = ["firefly_dworkers", "firefly_dworkers_cli", "firefly_dworkers_server"]`.

### Type Hints

- Use modern type syntax (`list[str]` not `List[str]`, `str | None` not `Optional[str]`).
- Use `TYPE_CHECKING` blocks for imports only needed for type hints to avoid circular imports.

### Thread Safety

- All registries must use `threading.Lock` for read/write operations.
- Use `contextvars.ContextVar` for per-request state in async contexts.

### Naming

- Modules: `snake_case`
- Classes: `PascalCase`
- Functions and methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: prefix with `_`

---

## Adding a New Tool

1. Choose the appropriate port (abstract base class) or create a new one.
2. Create a new module under the relevant `tools/` subdirectory.
3. Implement the required abstract methods.
4. Decorate with `@tool_registry.register("name", category="category")`.
5. Add the import to `firefly_dworkers/tools/__init__.py`.
6. Add tests in the corresponding `tests/test_tools/` directory.
7. Document any new optional dependencies in `pyproject.toml`.

Example -- adding a Brave Search adapter:

```python
# src/firefly_dworkers/tools/web/brave.py
from __future__ import annotations

from firefly_dworkers.tools.registry import tool_registry
from firefly_dworkers.tools.web.search import SearchResult, WebSearchTool


@tool_registry.register("brave", category="web_search")
class BraveSearchTool(WebSearchTool):
    """Brave Search API adapter."""

    def __init__(self, *, api_key: str, max_results: int = 10):
        super().__init__(max_results=max_results)
        self._api_key = api_key

    async def _search(self, query: str, max_results: int) -> list[SearchResult]:
        # Implementation using Brave Search API
        ...
```

Then add the import trigger in `tools/__init__.py`:

```python
import firefly_dworkers.tools.web.brave  # noqa: F401  # registers "brave"
```

See [Tool Registry](tools/registry.md) for details.

---

## Adding a New Worker

1. Add a new value to the `WorkerRole` enum in `types.py`.
2. Create a new module under `workers/`.
3. Extend `BaseWorker`.
4. Decorate with `@worker_factory.register(WorkerRole.YOUR_ROLE)`.
5. Implement `_build_instructions()` and toolkit selection.
6. Add the import to `firefly_dworkers/workers/__init__.py`.
7. Add tests in `tests/test_workers/`.

Example -- adding a QA reviewer worker:

```python
# src/firefly_dworkers/workers/qa_reviewer.py
from __future__ import annotations

from firefly_dworkers.workers.base import BaseWorker
from firefly_dworkers.workers.factory import worker_factory
from firefly_dworkers.types import WorkerRole


@worker_factory.register(WorkerRole.QA_REVIEWER)
class QAReviewerWorker(BaseWorker):
    """Worker specialized in quality assurance and review tasks."""
    ...
```

See [Custom Workers](workers/custom-workers.md) for details.

---

## Adding a New Plan Template

1. Create a new module under `plans/templates/`.
2. Define a function that returns a `BasePlan` with `PlanStep` instances.
3. Register it in `plans/templates/__init__.py`.
4. Add tests in `tests/test_plans/`.

See [Custom Plans](plans/custom-plans.md) for details.

---

## Adding a New Vertical

1. Create a new module under `verticals/`.
2. Define a `VerticalConfig` instance and call `register_vertical()`.
3. Add the import to `firefly_dworkers/verticals/__init__.py`.
4. Add tests in `tests/test_verticals/`.

See [Verticals Overview](verticals/overview.md) for details.

---

## Build System

The project uses [uv_build](https://docs.astral.sh/uv/) as the build backend:

```toml
[build-system]
requires = ["uv_build>=0.9.5,<0.10.0"]
build-backend = "uv_build"
```

To build a distribution:

```bash
uv build
```

---

## Test Organization

Tests follow a consistent pattern:

```
tests/
|-- conftest.py                    # Shared fixtures
|-- test_config.py                 # Global DworkersConfig tests
|-- test_types.py                  # WorkerRole, AutonomyLevel enums
|-- test_workers/
|   |-- test_base.py               # BaseWorker tests
|   |-- test_factory.py            # WorkerFactory tests
|   |-- test_registry.py           # WorkerRegistry tests
|-- test_tools/
|   |-- test_registry.py           # ToolRegistry tests
|   |-- test_toolkits.py           # Toolkit factory tests
|   |-- test_web/                  # WebSearchTool, WebBrowsingTool, Tavily, SerpAPI
|   |-- test_storage/              # SharePoint, GoogleDrive, Confluence, S3
|   |-- test_communication/        # Slack, Teams, Email
|   |-- test_project/              # Jira, Asana
|   |-- test_consulting/           # Consulting tools
|   |-- test_data/                 # CSV/Excel, SQL, API client
|-- test_plans/                    # BasePlan, PlanBuilder tests
|-- test_tenants/                  # TenantConfig, TenantLoader tests
|-- test_knowledge/                # KnowledgeBackend, KnowledgeRepository tests
|-- test_sdk/                      # DworkersClient, AsyncDworkersClient tests
|-- test_server/                   # FastAPI app tests
|-- test_cli/                      # CLI command tests
|-- test_autonomy/                 # Checkpoint, autonomy level tests
|-- test_verticals/                # Vertical config tests
|-- test_integration/              # End-to-end integration tests
```

### Writing Tests

- Use `pytest` fixtures for setup/teardown.
- Call `.clear()` on registries in fixtures to avoid state leakage.
- Use `TenantConfig(id="test", name="Test")` for minimal test configs.
- Async tests are auto-detected (no `@pytest.mark.asyncio` needed).

---

## Commit Guidelines

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short summary>
```

**Types:**

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Build system, CI, dependencies |

**Examples:**

```
feat(tools): add FlyBrowser adapter for browser automation
fix(registry): prevent silent overwrites on duplicate registration
test(factory): add thread-safety tests for WorkerFactory
docs(knowledge): add KnowledgeBackend protocol reference
refactor(toolkits): replace hardcoded imports with registry lookups
```

Keep commit messages concise (under 72 characters for the summary line). Use the body for additional context when the change is not self-explanatory.

---

## Related Documentation

- [Architecture](architecture.md) -- System design overview
- [Tool Registry](tools/registry.md) -- Tool registration pattern
- [Custom Workers](workers/custom-workers.md) -- Worker creation pattern
- [Custom Plans](plans/custom-plans.md) -- Plan creation pattern
