"""Interactive question widget — inline numbered options with arrow-key navigation.

Mounted in the chat area when the AI asks a question. The user navigates
with Up/Down arrows, confirms with Enter, or presses Tab to switch to
free-form text input.
"""

from __future__ import annotations

from typing import Any

from textual import events
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import Input, Static


class InteractiveQuestion(Vertical):
    """Inline question with selectable options."""

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
        yield Static(self._format_options(), id="question-options", classes="question-options")
        yield Static(
            "  \u2191\u2193 navigate \u00b7 enter to select \u00b7 tab for free input",
            classes="question-hint",
        )

    def _format_options(self) -> str:
        lines = []
        for i, opt in enumerate(self._options):
            marker = "\u276f" if i == self._selected else " "
            lines.append(f"  {marker} {i + 1}. {opt}")
        return "\n".join(lines)

    def _refresh_options(self) -> None:
        try:
            self.query_one("#question-options", Static).update(self._format_options())
        except NoMatches:
            pass

    def move(self, delta: int) -> None:
        """Move selection by delta."""
        old = self._selected
        self._selected = max(0, min(len(self._options) - 1, self._selected + delta))
        if old != self._selected:
            self._refresh_options()

    @property
    def selected_option(self) -> str:
        return self._options[self._selected]

    def toggle_free_form(self) -> None:
        """Toggle between option selection and free-form text input."""
        self._free_form = not self._free_form
        if self._free_form:
            try:
                self.query_one("#question-options", Static).display = False
                self.mount(Input(placeholder="Type your answer...", id="free-input"))
                self.query_one("#free-input", Input).focus()
            except Exception:
                pass
        else:
            try:
                self.query_one("#free-input", Input).remove()
                self.query_one("#question-options", Static).display = True
            except Exception:
                pass

    def _submit_answer(self, choice: str, index: int | None = None) -> None:
        """Post the answer and collapse the widget."""
        if self._answered:
            return
        self._answered = True
        self.post_message(self.Answered(choice, index))
        # Collapse to show chosen answer
        for child in list(self.children):
            child.remove()
        display = f"  > {index + 1}. {choice}" if index is not None else f"  > {choice}"
        self.mount(Static(display, classes="question-answered"))

    async def on_key(self, event: events.Key) -> None:
        """Handle navigation keys."""
        if self._answered:
            return
        if self._free_form:
            if event.key == "escape" or event.key == "tab":
                self.toggle_free_form()
                event.stop()
            elif event.key == "enter":
                try:
                    text = self.query_one("#free-input", Input).value.strip()
                    if text:
                        self._submit_answer(text)
                except Exception:
                    pass
                event.stop()
        else:
            if event.key == "up":
                self.move(-1)
                event.stop()
            elif event.key == "down":
                self.move(1)
                event.stop()
            elif event.key == "enter":
                self._submit_answer(self.selected_option, self._selected)
                event.stop()
            elif event.key == "tab":
                self.toggle_free_form()
                event.stop()
            elif event.key == "escape":
                self._submit_answer(self.selected_option, self._selected)
                event.stop()
