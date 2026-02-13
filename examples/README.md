# Firefly Digital Workers — Working Examples

Runnable examples demonstrating the firefly-dworkers platform with the
Anthropic Claude API. Each example is self-contained and can be executed
independently.

## Prerequisites

1. **Anthropic API key** — export it as an environment variable (never hardcode):

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. **Install dependencies** — from the repository root:

   ```bash
   uv sync --all-extras   # includes anthropic, python-pptx, etc.
   ```

## Running Examples

From the repository root:

```bash
# 01 — Simplest example: single analyst worker
uv run python examples/01_basic_analyst.py

# 02 — Researcher producing a structured market brief
uv run python examples/02_research_brief.py

# 03 — Data analyst with inline CSV data
uv run python examples/03_data_analysis.py

# 04 — Multi-worker plan execution (async DAG)
uv run python examples/04_multi_worker_plan.py

# 05 — Real-time token streaming (async)
uv run python examples/05_streaming.py

# 06 — Analyst + PowerPoint tool → .pptx file
uv run python examples/06_presentation_tool.py
```

## What Each Example Demonstrates

| # | File | Workers / Tools | Pattern |
|---|------|-----------------|---------|
| 1 | `01_basic_analyst.py` | AnalystWorker | Synchronous `run_sync()` |
| 2 | `02_research_brief.py` | ResearcherWorker | Synchronous `run_sync()` with `report_generation` tool |
| 3 | `03_data_analysis.py` | DataAnalystWorker | Synchronous `run_sync()` with inline CSV data |
| 4 | `04_multi_worker_plan.py` | Analyst + Researcher + DataAnalyst + Manager | Async `PlanBuilder` DAG execution |
| 5 | `05_streaming.py` | AnalystWorker | Async streaming via `run_stream()` |
| 6 | `06_presentation_tool.py` | AnalystWorker + PowerPointTool | Two-phase: LLM generates content, tool creates `.pptx` |

## Notes

- All examples use `anthropic:claude-sonnet-4-5-20250929` as the default model.
- The `ANTHROPIC_API_KEY` environment variable is read automatically by the
  underlying pydantic-ai framework.
- Examples 4, 5, and 6 use `asyncio.run()` for async execution.
- Example 6 writes a `strategy_deck.pptx` file to the current directory.
