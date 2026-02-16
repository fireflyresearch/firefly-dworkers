"""Interactive question widget --- inline numbered options with arrow-key navigation.

Mounted in the input area (replacing the prompt) when the AI asks a question.
The user navigates with Up/Down arrows, confirms with Enter, or presses Tab
to switch to free-form text input.  Options are also clickable with the mouse.
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
        def __init__(self, index: int, text: str) -> None:
            super().__init__()
            self.index = index
            self.text = text

    def __init__(self, text: str, index: int, **kwargs: Any) -> None:
        super().__init__(text, **kwargs)
        self._option_text = text
        self._option_index = index

    def on_click(self) -> None:
        self.post_message(self.Clicked(self._option_index, self._option_text))


class InteractiveQuestion(Vertical, can_focus=True):
    """Inline question with selectable options.

    Mounted in the input area (replacing the prompt) when the AI asks a
    numbered question. Arrow keys navigate, Enter confirms, Tab switches
    to free-form text input.  Options are also clickable with the mouse.
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
            yield OptionItem(f"  {marker} {i + 1}. {opt}", index=i, classes="question-option")
        yield Static(
            "  \u2191\u2193 navigate \u00b7 enter to select \u00b7 tab for free input \u00b7 click to choose",
            classes="question-hint",
        )

    def _format_options(self) -> str:
        """Format options as a single string (kept for backward compatibility)."""
        lines = []
        for i, opt in enumerate(self._options):
            marker = "\u276f" if i == self._selected else " "
            lines.append(f"  {marker} {i + 1}. {opt}")
        return "\n".join(lines)

    def _refresh_options(self) -> None:
        for i, item in enumerate(self.query(OptionItem)):
            marker = "\u276f" if i == self._selected else " "
            item.update(f"  {marker} {i + 1}. {self._options[i]}")

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

    def on_option_item_clicked(self, event: OptionItem.Clicked) -> None:
        """Handle click on an option item."""
        self._selected = event.index
        self._refresh_options()
        self._submit_answer(event.text, event.index)
        event.stop()

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

    async def on_key(self, event: events.Key) -> None:
        """Handle navigation keys when in option selection mode."""
        if self._answered:
            return
        # Free-form keys (Tab/Escape/Enter) handled via QuestionInput messages
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
