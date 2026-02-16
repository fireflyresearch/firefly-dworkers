# Phase 1: Fix Critical Bugs — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the three critical bugs in plan execution: EOF errors crash steps (no retry), interactive questions don't work during plans, and the question widget isn't clickable.

**Architecture:** Add a `RetryPolicy` helper for retryable error detection and backoff. Extend `_execute_approved_plan()` with question detection between steps and an `asyncio.Event` pause mechanism. Add `on_click()` to `InteractiveQuestion` option rows.

**Tech Stack:** Python 3.12, Textual 7.5.0, asyncio, pytest

---

### Task 1: RetryPolicy Helper

**Files:**
- Create: `src/firefly_dworkers_cli/tui/retry_policy.py`
- Test: `tests/test_tui/test_retry_policy.py`

**Step 1: Write the failing tests**

```python
# tests/test_tui/test_retry_policy.py
"""Tests for the RetryPolicy helper."""

import pytest

from firefly_dworkers_cli.tui.retry_policy import RetryPolicy


class TestRetryPolicy:
    def test_default_max_retries(self):
        policy = RetryPolicy()
        assert policy.max_retries == 3

    def test_is_retryable_eof_error(self):
        policy = RetryPolicy()
        assert policy.is_retryable("EOF while parsing an object at line 1 column 58")

    def test_is_retryable_json_decode(self):
        policy = RetryPolicy()
        assert policy.is_retryable("Expecting value: line 1 column 1 (char 0)")

    def test_is_retryable_incomplete_response(self):
        policy = RetryPolicy()
        assert policy.is_retryable("Incomplete JSON")

    def test_not_retryable_generic_error(self):
        policy = RetryPolicy()
        assert not policy.is_retryable("Connection refused")

    def test_not_retryable_auth_error(self):
        policy = RetryPolicy()
        assert not policy.is_retryable("Authentication failed: invalid API key")

    def test_backoff_delay_exponential(self):
        policy = RetryPolicy(base_delay=2.0)
        assert policy.delay_for_attempt(1) == 2.0
        assert policy.delay_for_attempt(2) == 4.0
        assert policy.delay_for_attempt(3) == 8.0

    def test_should_retry_within_max(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(1, "EOF while parsing")
        assert policy.should_retry(2, "EOF while parsing")
        assert policy.should_retry(3, "EOF while parsing")

    def test_should_not_retry_over_max(self):
        policy = RetryPolicy(max_retries=3)
        assert not policy.should_retry(4, "EOF while parsing")

    def test_should_not_retry_non_retryable(self):
        policy = RetryPolicy()
        assert not policy.should_retry(1, "Connection refused")

    def test_format_retry_message(self):
        policy = RetryPolicy()
        msg = policy.format_retry_message("Leo", 3, 6, 2)
        assert "Retrying" in msg
        assert "Leo" in msg
        assert "2/3" in msg

    def test_format_failure_message(self):
        policy = RetryPolicy()
        msg = policy.format_failure_message("Leo", 3, 6, "EOF while parsing")
        assert "failed" in msg.lower()
        assert "Leo" in msg
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tui/test_retry_policy.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'firefly_dworkers_cli.tui.retry_policy'"

**Step 3: Write the implementation**

```python
# src/firefly_dworkers_cli/tui/retry_policy.py
"""Retry policy for plan step execution.

Detects retryable errors (JSON parsing, EOF, incomplete response) and provides
exponential backoff delays. Non-retryable errors (auth, connection) fail immediately.
"""

from __future__ import annotations

import re

# Patterns that indicate a retryable (transient/model) error
_RETRYABLE_PATTERNS = [
    re.compile(r"EOF while parsing", re.IGNORECASE),
    re.compile(r"Expecting (?:value|property name|',')", re.IGNORECASE),
    re.compile(r"Incomplete JSON", re.IGNORECASE),
    re.compile(r"Unterminated string", re.IGNORECASE),
    re.compile(r"Invalid (?:control character|escape)", re.IGNORECASE),
    re.compile(r"Extra data", re.IGNORECASE),
    re.compile(r"JSONDecodeError", re.IGNORECASE),
]


class RetryPolicy:
    """Encapsulates retry logic for plan step execution."""

    def __init__(self, max_retries: int = 3, base_delay: float = 2.0) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay

    def is_retryable(self, error_msg: str) -> bool:
        """Check if the error message indicates a retryable failure."""
        return any(p.search(error_msg) for p in _RETRYABLE_PATTERNS)

    def delay_for_attempt(self, attempt: int) -> float:
        """Return the backoff delay in seconds for the given attempt number."""
        return self.base_delay * (2 ** (attempt - 1))

    def should_retry(self, attempt: int, error_msg: str) -> bool:
        """Determine if a retry should be attempted."""
        return attempt <= self.max_retries and self.is_retryable(error_msg)

    def format_retry_message(
        self, agent_name: str, step: int, total: int, attempt: int
    ) -> str:
        """Format a user-facing retry message."""
        return (
            f"\u27f3 Retrying step {step}/{total} ({agent_name})... "
            f"(attempt {attempt}/{self.max_retries})"
        )

    def format_failure_message(
        self, agent_name: str, step: int, total: int, error_msg: str
    ) -> str:
        """Format a user-facing failure message after all retries exhausted."""
        return (
            f"\u2717 Step {step}/{total} ({agent_name}) failed after "
            f"{self.max_retries} attempts: {error_msg}. "
            f"Continuing with remaining steps."
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tui/test_retry_policy.py -v`
Expected: All 12 tests PASS

**Step 5: Commit**

```bash
git add src/firefly_dworkers_cli/tui/retry_policy.py tests/test_tui/test_retry_policy.py
git commit -m "feat(tui): add RetryPolicy helper for plan step error recovery"
```

---

### Task 2: Wire Retry into Plan Execution

**Files:**
- Modify: `src/firefly_dworkers_cli/tui/app.py` — `_execute_approved_plan()` (~line 1344)
- Test: `tests/test_tui/test_plan_detection.py` (add retry-related tests)

**Step 1: Write the failing tests**

Add to `tests/test_tui/test_plan_detection.py`:

```python
class TestRetryableErrorDetection:
    """Test that plan execution identifies retryable errors."""

    def test_eof_error_is_retryable(self):
        from firefly_dworkers_cli.tui.retry_policy import RetryPolicy
        policy = RetryPolicy()
        assert policy.is_retryable("EOF while parsing an object at line 1 column 58")

    def test_json_error_is_retryable(self):
        from firefly_dworkers_cli.tui.retry_policy import RetryPolicy
        policy = RetryPolicy()
        assert policy.is_retryable("Expecting value: line 1 column 1 (char 0)")

    def test_connection_error_not_retryable(self):
        from firefly_dworkers_cli.tui.retry_policy import RetryPolicy
        policy = RetryPolicy()
        assert not policy.is_retryable("Connection refused")
```

**Step 2: Run to verify they pass** (they depend on Task 1)

Run: `uv run pytest tests/test_tui/test_plan_detection.py -v`
Expected: PASS

**Step 3: Modify `_execute_approved_plan()` to use retry**

In `src/firefly_dworkers_cli/tui/app.py`, add import at top:

```python
from firefly_dworkers_cli.tui.retry_policy import RetryPolicy
```

Then replace the step execution loop inside `_execute_approved_plan()`. The key change is wrapping the `async for event in self._client.run_worker(...)` block in a retry loop:

```python
async def _execute_approved_plan(self) -> None:
    """Execute the approved plan steps sequentially with full progress feedback."""
    if not self._pending_plan or not self._client:
        return

    steps = self._pending_plan
    self._pending_plan = None

    # Remove approval widget
    with contextlib.suppress(NoMatches):
        for w in self.query(".plan-approval"):
            w.remove()

    # Auto-invite all plan agents to conversation participants
    if self._conversation:
        for role, _ in steps:
            if role not in self._conversation.participants and role != "user":
                self._conversation.participants.append(role)
        self._update_participants_display()

    # Build participant info for context injection
    participant_info: list[tuple[str, str, str]] = []
    if self._conversation and self._conversation.participants:
        for p in self._conversation.participants:
            if p == "user":
                continue
            pname, _avatar, _color = self._get_worker_display(p)
            desc = self._role_descriptions.get(p, "")
            participant_info.append((p, pname, desc))

    message_list = self.query_one("#message-list", VerticalScroll)
    self._is_streaming = True
    self._update_toolbar()
    retry_policy = RetryPolicy()

    try:
        for i, (role, task) in enumerate(steps, 1):
            name, avatar, avatar_color = self._get_worker_display(role)
            prefix = f"({avatar}) " if avatar else ""
            avatar_cls = f" avatar-{avatar_color}" if avatar_color else ""

            # Step header
            step_box = Vertical(classes="msg-box-ai")
            await message_list.mount(step_box)
            await step_box.mount(
                Static(
                    f"Step {i}/{len(steps)}: {prefix}{name}",
                    classes=f"msg-sender msg-sender-ai{avatar_cls}",
                )
            )

            content_widget = RichResponseMarkdown("", classes="msg-content")
            await step_box.mount(content_widget)

            # Progress indicator
            indicator = TaskProgressBlock()
            await step_box.mount(indicator)
            message_list.scroll_end(animate=False)

            # Retry loop for this step
            attempt = 0
            step_succeeded = False
            tokens: list[str] = []

            while not step_succeeded:
                attempt += 1
                tokens = []
                first_token_marked = False
                last_render = 0.0
                step_error: str | None = None

                try:
                    history = self._build_message_history()
                    timer = ResponseTimer()
                    timer.start()

                    async for event in self._client.run_worker(
                        role,
                        task,
                        conversation_id=self._conversation.id if self._conversation else None,
                        message_history=history,
                        participants=participant_info,
                    ):
                        if self._cancel_streaming.is_set():
                            tokens.append("\n\n_[Plan cancelled]_")
                            await content_widget.update("".join(tokens))
                            timer.stop()
                            indicator.stop()
                            indicator.remove()
                            return
                        if event.type in ("token", "complete"):
                            if not first_token_marked:
                                first_token_marked = True
                                timer.mark_first_token()
                                indicator.set_streaming_mode(timer)
                            tokens.append(event.content)
                            now = time.monotonic()
                            if event.type == "complete" or now - last_render >= 0.08:
                                last_render = now
                                await content_widget.update("".join(tokens))
                                if self._is_near_bottom(message_list):
                                    message_list.scroll_end(animate=False)
                        elif event.type == "tool_call":
                            tool_box = Vertical(classes="tool-call")
                            await step_box.mount(tool_box, before=indicator)
                            await tool_box.mount(
                                Static(f"\u2699 {event.content}", classes="tool-call-header")
                            )
                            if self._is_near_bottom(message_list):
                                message_list.scroll_end(animate=False)
                        elif event.type == "error":
                            step_error = event.content
                    # If we got tokens, the step succeeded
                    if tokens and not step_error:
                        step_succeeded = True
                    elif step_error:
                        raise RuntimeError(step_error)
                    else:
                        step_succeeded = True  # empty but no error

                except Exception as e:
                    step_error = str(e)
                    timer.stop()

                    if retry_policy.should_retry(attempt, step_error):
                        retry_msg = retry_policy.format_retry_message(name, i, len(steps), attempt)
                        await content_widget.update(retry_msg)
                        if self._is_near_bottom(message_list):
                            message_list.scroll_end(animate=False)
                        delay = retry_policy.delay_for_attempt(attempt)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Final failure — show error and move on
                        if retry_policy.is_retryable(step_error):
                            fail_msg = retry_policy.format_failure_message(name, i, len(steps), step_error)
                        else:
                            fail_msg = f"\n\n**Error:** {step_error}"
                        tokens.append(fail_msg)
                        await content_widget.update("".join(tokens))
                        step_succeeded = True  # move to next step

                finally:
                    if step_succeeded or not retry_policy.should_retry(attempt, step_error or ""):
                        timer.stop()
                        indicator.stop()
                        indicator.remove()

            # Final flush
            final_content = "".join(tokens)
            await content_widget.update(final_content)

            # Token count update
            token_estimate = self._estimate_tokens(final_content)
            self._total_tokens += token_estimate
            with contextlib.suppress(NoMatches):
                self.query_one("#token-count", Static).update(
                    f" \u00b7 ~{self._total_tokens:,} tokens"
                )

            # Response summary footer
            summary = Static(timer.format_summary(token_estimate), classes="response-summary")
            await step_box.mount(summary)

            # Save step result
            if self._conversation:
                step_msg = ChatMessage(
                    id=f"msg_{uuid.uuid4().hex[:12]}",
                    conversation_id=self._conversation.id,
                    role=role,
                    sender=name,
                    content=final_content,
                    timestamp=datetime.now(UTC),
                    is_ai=True,
                )
                self._store.add_message(self._conversation.id, step_msg)

            # --- QUESTION DETECTION (Phase 1B) ---
            detected = self._detect_question(final_content)
            if detected is not None and i < len(steps):
                question_text, options = detected
                # Pause: mount question and wait for answer
                self._plan_answer_event = asyncio.Event()
                self._plan_answer_text: str | None = None
                await self._mount_plan_question(step_box, question_text, options)
                # Wait for user to answer
                await self._plan_answer_event.wait()
                # Inject answer as context for the next step
                if self._plan_answer_text:
                    next_role, next_task = steps[i]  # i is 1-indexed, steps[i] is next
                    steps[i] = (next_role, f"Context: The user answered '{self._plan_answer_text}' to the previous question.\n\n{next_task}")

    finally:
        self._is_streaming = False
        self._cancel_streaming.clear()
        self._update_toolbar()

    message_list.scroll_end(animate=False)
    self._update_input_hint()

    # Drain queued message
    if self._queued_message:
        queued = self._queued_message
        self._queued_message = None
        await self._handle_input(queued)
```

**Step 4: Run all tests to verify no regressions**

Run: `uv run pytest tests/test_tui/ -x -q`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/firefly_dworkers_cli/tui/app.py tests/test_tui/test_plan_detection.py
git commit -m "feat(tui): add retry with backoff for plan step execution errors"
```

---

### Task 3: Question Pause During Plan Execution

**Files:**
- Modify: `src/firefly_dworkers_cli/tui/app.py` — add `_mount_plan_question()`, `_on_plan_question_answered()`, `_plan_answer_event` / `_plan_answer_text` attrs
- Modify: `src/firefly_dworkers_cli/tui/widgets/interactive_question.py` — add `PlanAnswered` message variant

**Step 1: Add `_plan_answer_event` and `_plan_answer_text` to `__init__`**

In `app.py`, in `DworkersApp.__init__()`, after `self._pending_plan`:

```python
self._plan_answer_event: asyncio.Event | None = None
self._plan_answer_text: str | None = None
```

**Step 2: Add `_mount_plan_question()` method**

In `app.py`, after `_mount_question()`:

```python
async def _mount_plan_question(
    self,
    step_box: Vertical,
    question: str,
    options: list[str],
) -> None:
    """Mount an interactive question inside a plan step box (not in the input area).

    Unlike _mount_question(), this mounts the widget inside the step's message
    box and pauses plan execution until the user answers.
    """
    from firefly_dworkers_cli.tui.widgets.interactive_question import InteractiveQuestion

    widget = InteractiveQuestion(question=question, options=options, id="plan-question")
    await step_box.mount(widget)
    widget.focus()

    # Update toolbar to show question state
    self._update_toolbar()

    message_list = self.query_one("#message-list", VerticalScroll)
    message_list.scroll_end(animate=False)
```

**Step 3: Modify `on_interactive_question_answered` to handle plan questions**

Replace the existing handler in `app.py`:

```python
async def on_interactive_question_answered(self, event) -> None:
    """Handle the user's answer to an interactive question."""
    from firefly_dworkers_cli.tui.widgets.interactive_question import InteractiveQuestion

    # Check if this is a plan-step question (mounted inside a step box)
    if self._plan_answer_event is not None:
        # Plan question: store answer and signal the waiting plan executor
        self._plan_answer_text = event.choice

        # Show the answer inline and remove the question widget
        for widget in self.query(InteractiveQuestion):
            # Replace question with answer display
            parent = widget.parent
            await widget.remove()
            if parent is not None:
                answer_display = Static(
                    f"\u2714 You answered: {event.choice}",
                    classes="question-answered",
                )
                await parent.mount(answer_display)

        # Signal the plan executor to continue
        self._plan_answer_event.set()
        self._plan_answer_event = None
        return

    # Regular (non-plan) question: existing behavior
    for widget in self.query(InteractiveQuestion):
        await widget.remove()

    input_area = self.query_one("#input-area", Vertical)
    input_area.remove_class("question-active")
    try:
        self.query_one("#input-row").display = True
        self.query_one("#input-hint").display = True
    except NoMatches:
        pass

    self.query_one("#prompt-input", PromptInput).focus()
    await self._handle_input(event.choice)
```

**Step 4: Run all tests**

Run: `uv run pytest tests/test_tui/ -x -q`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/firefly_dworkers_cli/tui/app.py
git commit -m "feat(tui): pause plan execution when agent asks interactive question"
```

---

### Task 4: Add Click Support to InteractiveQuestion

**Files:**
- Modify: `src/firefly_dworkers_cli/tui/widgets/interactive_question.py`
- Test: `tests/test_tui/test_interactive_question.py`

**Step 1: Write the failing test**

Add to `tests/test_tui/test_interactive_question.py`:

```python
class TestClickableOptions:
    def test_option_items_are_created(self):
        """Verify compose yields OptionItem children."""
        q = InteractiveQuestion(
            question="Pick:", options=["Alpha", "Beta", "Gamma"]
        )
        # After the refactor, compose should yield OptionItem widgets
        children = list(q.compose())
        # Should have: question text, option items, hint
        option_items = [c for c in children if isinstance(c, OptionItem)]
        assert len(option_items) == 3

    def test_option_item_stores_index_and_text(self):
        item = OptionItem("Alpha", 0)
        assert item._option_text == "Alpha"
        assert item._option_index == 0
```

**Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_tui/test_interactive_question.py::TestClickableOptions -v`
Expected: FAIL with "cannot import name 'OptionItem'"

**Step 3: Refactor InteractiveQuestion to use clickable OptionItem widgets**

Replace the current `_format_options()` / `Static` approach with individual `OptionItem` widgets:

```python
# src/firefly_dworkers_cli/tui/widgets/interactive_question.py
"""Interactive question widget — inline numbered options with arrow-key navigation.

Mounted in the input area (replacing the prompt) when the AI asks a question.
The user navigates with Up/Down arrows, confirms with Enter, clicks an option,
or presses Tab to switch to free-form text input.
"""

from __future__ import annotations

from typing import Any

from textual import events
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import Input, Static


class QuestionInput(Input):
    """Free-form input that delegates Tab/Escape to parent via messages."""

    class ExitFreeForm(Message):
        """Posted when user presses Tab or Escape in free-form mode."""

    async def _on_key(self, event: events.Key) -> None:
        if event.key in ("tab", "escape"):
            event.stop()
            event.prevent_default()
            self.post_message(self.ExitFreeForm())
            return
        await super()._on_key(event)


class OptionItem(Static):
    """A single clickable option row."""

    class Clicked(Message):
        """Posted when the user clicks this option."""
        def __init__(self, index: int, text: str) -> None:
            super().__init__()
            self.index = index
            self.text = text

    def __init__(self, text: str, index: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._option_text = text
        self._option_index = index

    def on_click(self) -> None:
        self.post_message(self.Clicked(self._option_index, self._option_text))


class InteractiveQuestion(Vertical, can_focus=True):
    """Inline question with selectable options.

    Mounted in the input area (replacing the prompt) when the AI asks a
    numbered question. Arrow keys navigate, Enter confirms, click selects,
    Tab switches to free-form text input.
    """

    class Answered(Message):
        """Posted when the user picks an option or submits free text."""

        def __init__(self, choice: str, index: int | None = None) -> None:
            super().__init__()
            self.choice = choice
            self.index = index

    def __init__(
        self,
        question: str,
        options: list[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(classes="interactive-question", **kwargs)
        self._question = question
        self._options = options
        self._selected = 0
        self._free_form = False
        self._answered = False

    def compose(self):
        yield Static(self._question, classes="question-text")
        for i, opt in enumerate(self._options):
            marker = "\u276f" if i == self._selected else " "
            yield OptionItem(
                f"  {marker} {i + 1}. {opt}",
                index=i,
                classes="question-option",
            )
        yield Static(
            "  \u2191\u2193 navigate \u00b7 enter to select \u00b7 tab for free input \u00b7 click to choose",
            classes="question-hint",
        )

    def _refresh_options(self) -> None:
        """Update visual markers on all option items."""
        for i, item in enumerate(self.query(OptionItem)):
            marker = "\u276f" if i == self._selected else " "
            item.update(f"  {marker} {i + 1}. {self._options[i]}")

    def _format_options(self) -> str:
        """Format options as a string (for backward compatibility in tests)."""
        lines = []
        for i, opt in enumerate(self._options):
            marker = "\u276f" if i == self._selected else " "
            lines.append(f"  {marker} {i + 1}. {opt}")
        return "\n".join(lines)

    def move(self, delta: int) -> None:
        """Move selection by delta."""
        old = self._selected
        self._selected = max(0, min(len(self._options) - 1, self._selected + delta))
        if old != self._selected:
            self._refresh_options()

    @property
    def selected_option(self) -> str:
        return self._options[self._selected]

    async def toggle_free_form(self) -> None:
        """Toggle between option selection and free-form text input."""
        self._free_form = not self._free_form
        if self._free_form:
            try:
                for item in self.query(OptionItem):
                    item.display = False
                self.query_one(".question-hint", Static).update(
                    "  type your answer \u00b7 enter to submit \u00b7 tab/esc to go back"
                )
                await self.mount(QuestionInput(placeholder="Type your answer...", id="free-input"))
                self.query_one("#free-input", QuestionInput).focus()
            except Exception:
                pass
        else:
            try:
                inp = self.query_one("#free-input", QuestionInput)
                await inp.remove()
                for item in self.query(OptionItem):
                    item.display = True
                self.query_one(".question-hint", Static).update(
                    "  \u2191\u2193 navigate \u00b7 enter to select \u00b7 tab for free input \u00b7 click to choose"
                )
                self.focus()
            except Exception:
                pass

    def _submit_answer(self, choice: str, index: int | None = None) -> None:
        """Post the answer."""
        if self._answered:
            return
        self._answered = True
        self.post_message(self.Answered(choice, index))

    async def on_question_input_exit_free_form(
        self, event: QuestionInput.ExitFreeForm
    ) -> None:
        """Handle Tab/Escape in free-form input."""
        await self.toggle_free_form()
        event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in free-form input."""
        if self._free_form and not self._answered:
            text = event.value.strip()
            if text:
                self._submit_answer(text)
        event.stop()

    def on_option_item_clicked(self, event: OptionItem.Clicked) -> None:
        """Handle click on an option item."""
        self._selected = event.index
        self._refresh_options()
        self._submit_answer(event.text, event.index)
        event.stop()

    async def on_key(self, event: events.Key) -> None:
        """Handle navigation keys when in option selection mode."""
        if self._answered:
            return
        if not self._free_form:
            if event.key == "up":
                self.move(-1)
                event.stop()
                event.prevent_default()
            elif event.key == "down":
                self.move(1)
                event.stop()
                event.prevent_default()
            elif event.key == "enter":
                self._submit_answer(self.selected_option, self._selected)
                event.stop()
                event.prevent_default()
            elif event.key == "tab":
                await self.toggle_free_form()
                event.stop()
                event.prevent_default()
            elif event.key == "escape":
                self._submit_answer(self.selected_option, self._selected)
                event.stop()
                event.prevent_default()
```

**Step 4: Update existing tests for OptionItem compose changes**

The existing `test_format_display_shows_marker` test still passes because `_format_options()` is preserved. Add the new OptionItem tests.

**Step 5: Add CSS for clickable options**

In `theme.py`, after the `.question-hint` rule:

```css
.question-option {
    height: 1;
    width: 1fr;
    padding: 0;
    color: #d4d4d4;
}

.question-option:hover {
    background: #333333;
    color: #ffffff;
}
```

**Step 6: Run all tests**

Run: `uv run pytest tests/test_tui/test_interactive_question.py -v`
Expected: All PASS

Run: `uv run pytest tests/ -x -q --ignore=tests/test_cli/test_commands.py -k "not test_no_args"`
Expected: All PASS (full suite)

**Step 7: Commit**

```bash
git add src/firefly_dworkers_cli/tui/widgets/interactive_question.py tests/test_tui/test_interactive_question.py src/firefly_dworkers_cli/tui/theme.py
git commit -m "feat(tui): add click support to interactive question options"
```

---

### Task 5: Add Multi-Word Role Plan Detection Tests

**Files:**
- Test: `tests/test_tui/test_plan_detection.py` (verify recent regex fix)

**Step 1: Add tests for multi-word roles**

Add to `tests/test_tui/test_plan_detection.py`:

```python
class TestMultiWordRoles:
    def test_detects_multi_word_role(self):
        app = _make_app()
        content = """Plan:
1. [content writer] Draft the blog post
2. [data analyst] Review the metrics
"""
        result = app._detect_plan(content)
        assert result is not None
        assert len(result) == 2
        assert result[0] == ("content_writer", "Draft the blog post")
        assert result[1] == ("data_analyst", "Review the metrics")

    def test_normalizes_spaces_to_underscores(self):
        app = _make_app()
        content = """Plan:
1. [Communications Specialist] Localize content
2. [strategist] Define strategy
"""
        result = app._detect_plan(content)
        assert result is not None
        assert result[0][0] == "communications_specialist"
        assert result[1][0] == "strategist"
```

**Step 2: Run to verify they pass** (regex was already fixed)

Run: `uv run pytest tests/test_tui/test_plan_detection.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_tui/test_plan_detection.py
git commit -m "test(tui): add multi-word role plan detection tests"
```

---

### Task 6: Update Toolbar for Question State

**Files:**
- Modify: `src/firefly_dworkers_cli/tui/app.py` — `_update_toolbar()`

**Step 1: Add question-pending state to toolbar**

In `_update_toolbar()`, add a check for `_plan_answer_event` before the streaming check:

```python
def _update_toolbar(self) -> None:
    """Update the contextual toolbar based on current app state."""
    with contextlib.suppress(NoMatches):
        toolbar = self.query_one("#toolbar", Static)
        if self._plan_answer_event is not None:
            toolbar.update("[↑↓] Navigate  [Enter] Select  [Tab] Free input  [Click] Choose")
            toolbar.set_class(True, "toolbar-plan")
            toolbar.set_class(False, "toolbar-streaming", "toolbar-default")
        elif self._pending_plan is not None:
            toolbar.update("[Enter] Approve  [m] Modify  [Esc] Skip")
            toolbar.set_class(True, "toolbar-plan")
            toolbar.set_class(False, "toolbar-streaming", "toolbar-default")
        elif self._is_streaming:
            toolbar.update("[Esc] Cancel")
            toolbar.set_class(True, "toolbar-streaming")
            toolbar.set_class(False, "toolbar-plan", "toolbar-default")
        elif self._private_role:
            name, _, _ = self._get_worker_display(self._private_role)
            toolbar.update(f"Private: @{name} \u00b7 [Esc] Exit private")
            toolbar.set_class(True, "toolbar-default")
            toolbar.set_class(False, "toolbar-plan", "toolbar-streaming")
        else:
            toolbar.update("/plan \u00b7 /team \u00b7 /project \u00b7 /help \u00b7 Ctrl+P all commands")
            toolbar.set_class(True, "toolbar-default")
            toolbar.set_class(False, "toolbar-plan", "toolbar-streaming")
```

**Step 2: Run all tests**

Run: `uv run pytest tests/ -x -q --ignore=tests/test_cli/test_commands.py -k "not test_no_args"`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/firefly_dworkers_cli/tui/app.py
git commit -m "feat(tui): toolbar shows question navigation hints during plan questions"
```

---

### Task 7: Final Integration Verification

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -x -q --ignore=tests/test_cli/test_commands.py -k "not test_no_args"`
Expected: All PASS

**Step 2: Push**

```bash
git push
```

---

## Summary of Phase 1 Changes

| Task | Files | What |
|------|-------|------|
| 1 | `retry_policy.py` (new), test | RetryPolicy helper |
| 2 | `app.py` | Wire retry into `_execute_approved_plan()` |
| 3 | `app.py` | Question pause: `_mount_plan_question()`, event-based wait |
| 4 | `interactive_question.py`, `theme.py`, test | Click support via OptionItem |
| 5 | test | Multi-word role detection tests |
| 6 | `app.py` | Toolbar question state |
| 7 | — | Integration verification |
