# Agent UX Overhaul — Claude Code Parity Design

**Date:** 2026-02-16
**Status:** Approved
**Approach:** Phased overhaul (4 phases, each deployable)

## Problem Statement

The TUI's multi-agent plan execution has critical UX gaps:

1. **Interactive questions don't work during plan execution** — `_detect_question()` only runs after `_send_message()`, never during plan steps. Numbered options render as inert text.
2. **No tool visibility** — Tool calls show only `⚙ description` with no parameters, file paths, status, or results.
3. **No agent coordination** — Plan steps run sequentially with no pause. If Step 5 asks a question, Step 6 starts immediately.
4. **EOF/JSON errors crash steps** — LLM returns truncated JSON; steps fail with raw error messages and no retry.
5. **No parallel execution** — Steps run one-at-a-time even when independent.

## Target: Claude Code Parity

| Feature | Claude Code | Dworkers Current | Dworkers Target |
|---------|-------------|------------------|-----------------|
| Tool display | Collapsible blocks with name, params, status, duration | `⚙ description` static text | ToolBlock widget, toggleable verbosity |
| Verbose mode | Ctrl+O toggle | None | Ctrl+O toggle (minimal ↔ verbose) |
| Questions | Permission prompts block execution | Only post-message, not during plans | Pause-and-prompt during plan steps |
| Parallelism | Up to 7 subagents | Sequential only | Parallel AgentLanes |
| Split panes | tmux/iTerm2 integration | None | Textual Grid-based split panes |
| Error handling | Retry + graceful degradation | Raw error text | Retry with backoff (3 attempts) |
| Subagent display | Named display with colors | Step N/M header only | AgentLane with avatar, role, status |

## Architecture

### Current Flow (Broken)

```
User Input → _handle_input() → _send_message() → run_worker() → StreamEvents
Plan Approval → _execute_approved_plan() → sequential for-loop → StreamEvents
                (no pause, no retry, no question detection)     → ⚙ Static text only
```

### Target Flow

```
User Input → _handle_input() → _send_message() → run_worker() → EnrichedStreamEvents
                                                                    ↓
Plan Approval → PlanExecutor → AgentLane(s) → run_worker()  → EnrichedStreamEvents
                  │                 │             ↓
                  ├─ RetryPolicy    ├─ parallel   ToolBlock (collapsible)
                  ├─ PauseOnQuestion├─ split-pane QuestionWidget (interactive)
                  └─ ProgressTracker└─ coordinated ErrorBadge (retry indicator)
```

### Key Abstractions

- **`PlanExecutor`** — Manages retry, pause, parallelism. Replaces inline for-loop.
- **`AgentLane`** — Per-agent scroll region with content, tools, questions, progress.
- **`ToolBlock`** — Collapsible widget replacing `Static("⚙ ...")`.
- **`RetryPolicy`** — Encapsulates retry logic (max 3 attempts, exponential backoff).
- **`EnrichedStreamEvent`** — StreamEvent with tool metadata (name, params, result, duration).

---

## Phase 1: Fix What's Broken

### 1A. EOF Error Retry

**Files:** `app.py` (`_execute_approved_plan`, `_send_message`)

- On `StreamEvent(type="error")` with JSON/EOF content, or zero tokens before error:
  - Show `"⟳ Retrying step 3/6... (attempt 2/3)"` in content widget
  - Wait with exponential backoff: 2s, 4s
  - Re-call `run_worker()` for same step
  - After 3 failures: error badge `"✗ Step 3/6 failed after 3 attempts"`, continue to next step
- `RetryPolicy` class: `max_retries=3`, `base_delay=2.0`, `is_retryable(error_msg) -> bool`

### 1B. Interactive Questions During Plan Execution

**Files:** `app.py` (`_execute_approved_plan`)

- After each step completes streaming, run `_detect_question()` on step content
- If question detected:
  - Mount `InteractiveQuestion` widget below the step
  - Set `asyncio.Event` — step loop awaits it
  - User answers via existing widget (arrow keys / Enter / Tab)
  - On answer: store answer, set event, continue to next step
  - Answer injected as context: `"The user answered: '{answer}' to the previous question."`

### 1C. Fix InteractiveQuestion Click Support

**Files:** `widgets/interactive_question.py`

- Add `on_click()` handler to each option row
- When clicked: select option and submit

### 1D. Graceful Error Display

**Replace:** `"Error: EOF while parsing an object at line 1 column 58"`
**With:** `"⚠ Step 3/6 (Leo) encountered an error — retrying (1/3)..."`
**After final failure:** `"✗ Step 3/6 (Leo) failed: Model returned incomplete response. Continuing with remaining steps."`

---

## Phase 2: Rich Tool Display

### 2A. Enriched StreamEvent

**Files:** `sdk/models.py`, `backend/local.py`

Populate existing `metadata` dict on tool_call events:
```python
StreamEvent(type="tool_call", content="Read",
    metadata={"tool_name": "Read", "params": {"file_path": "src/app.py"}, "status": "running"})

StreamEvent(type="tool_result", content="Read",  # NEW event type
    metadata={"tool_name": "Read", "status": "complete", "duration_ms": 120, "result_preview": "42 lines"})
```

### 2B. ToolBlock Widget

**New file:** `widgets/tool_block.py`

**Minimal view (default):**
```
  ⚙ Read src/app.py                              120ms ✓
  ⚙ Bash: git status                             ··· running
```

**Verbose view (Ctrl+O):**
```
  ⚙ Read src/app.py
    params: file_path="src/app.py", offset=1, limit=50
    result: 42 lines (1,204 chars)
    duration: 120ms
  ────────────────────────────────────
```

- Collapsible: click/keyboard to expand/collapse
- Status colors: running=amber, complete=green, error=red

### 2C. Verbose Mode Toggle

**Keybinding:** Ctrl+O toggles `self._verbose_mode: bool`
- Re-renders all visible ToolBlocks
- Status bar shows "verbose" indicator
- Session-scoped (not persisted)

### 2D. CSS

```css
.tool-block { height: auto; padding: 0 1; margin: 0 2 0 2; }
.tool-block-header { color: #888; height: 1; }
.tool-block-status-running { color: #f59e0b; }
.tool-block-status-complete { color: #10b981; }
.tool-block-status-error { color: #ef4444; }
.tool-block-details { display: none; color: #666; padding: 0 2; }
.tool-block-details.visible { display: block; }
```

---

## Phase 3: Parallel Execution Engine

### 3A. PlanExecutor

**New file:** `tui/plan_executor.py`

Replaces inline for-loop in `_execute_approved_plan()`:
- Analyzes step dependencies (default: all parallel unless explicitly dependent)
- Launches independent steps as concurrent `asyncio.Task`s
- Coordinates: pause events, cancellation, question queue
- Applies `RetryPolicy` per step

### 3B. AgentLane Widget

**New file:** `widgets/agent_lane.py`

Per-concurrent-agent `VerticalScroll` with:
- Agent header (name, avatar, role)
- Streaming content
- Tool blocks
- Progress indicator
- Question widget (when paused)

`LaneManager` creates/destroys lanes, handles focus routing, question events, cancellation.

### 3C. Question Coordination

- Paused agent's lane: amber border, "Waiting for your answer"
- Other agents continue running
- Multiple questions queue FIFO; first gets focus; badge "2 pending" on others
- User focuses lane (click or keyboard) and answers

### 3D. Cancellation

- **Esc** cancels all agents (extended from current)
- **Esc on focused lane** cancels only that agent
- Cancelled agents show `"[Cancelled]"` in their lane

---

## Phase 4: Split-Pane Display

### 4A. Layout Modes (Ctrl+L toggle)

**Inline mode** (default): All agents stream into same list with agent labels.

**Split-pane mode**: Grid layout with per-agent panes.
- 1 agent = full width
- 2 agents = side-by-side
- 3-4 agents = 2x2 grid
- 5-6 agents = 2x3 grid

### 4B. Textual Implementation

- `Grid` container with dynamic rows/columns
- Each cell is an `AgentLane`
- Focused pane: white border; others: dim border

### 4C. Navigation

- **Tab/Shift+Tab** — cycle pane focus
- **Click** — focus pane
- **Ctrl+L** — toggle inline ↔ split layout
- **Number keys 1-6** — jump to pane N in split mode

### 4D. Completion Flow

- Finished pane: `"✓ Complete — 2,143 tokens · 61.8s"`
- Shrinks to 2 lines, giving space to running agents
- All complete: collapse back to normal message list
- Combined output saved to conversation history

### 4E. CSS

```css
#split-pane-container { height: 1fr; }
.agent-lane { border: solid #444; height: 1fr; overflow-y: auto; }
.agent-lane:focus-within { border: solid #d4d4d4; }
.agent-lane-header { height: 1; background: #1a1a1a; padding: 0 1; }
.agent-lane-complete { height: 2; }
.agent-lane-waiting { border: solid #f59e0b; }
```

---

## Files Changed (Estimated)

### New Files
- `src/firefly_dworkers_cli/tui/plan_executor.py` — PlanExecutor, RetryPolicy
- `src/firefly_dworkers_cli/tui/widgets/tool_block.py` — ToolBlock widget
- `src/firefly_dworkers_cli/tui/widgets/agent_lane.py` — AgentLane, LaneManager

### Modified Files
- `src/firefly_dworkers/sdk/models.py` — Add `tool_result` event type
- `src/firefly_dworkers_cli/tui/backend/local.py` — Emit enriched tool events
- `src/firefly_dworkers_cli/tui/app.py` — Wire PlanExecutor, ToolBlock, verbose toggle, Ctrl+L/O bindings
- `src/firefly_dworkers_cli/tui/theme.py` — CSS for new widgets
- `src/firefly_dworkers_cli/tui/widgets/interactive_question.py` — Add click support

## Verification

Each phase should:
1. Pass all existing tests (`uv run pytest tests/ -x -q`)
2. Include new tests for added functionality
3. Be manually verified in the TUI with a multi-agent plan execution
