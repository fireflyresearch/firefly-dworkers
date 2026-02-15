"""Agent creation wizard — 4-step TUI wizard for creating custom agents."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static, TextArea

AVAILABLE_SKILLS = [
    ("research", "Research & web search"),
    ("data_analysis", "Data analysis & queries"),
    ("code_review", "Code review & analysis"),
    ("document_design", "Document design"),
    ("file_system", "File system access"),
    ("api_integrations", "API integrations"),
]

AVATAR_COLORS = ["red", "green", "blue", "cyan", "yellow", "magenta", "white"]


class AgentIdentityScreen(Screen):
    """Step 1/4: Agent name, avatar character, color."""

    CSS = """
    AgentIdentityScreen { align: center middle; }
    #wizard-container { width: 60; padding: 2 4; border: round $accent; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._name = ""
        self._avatar = ""
        self._color = "blue"

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static("Step 1/4: Agent Identity", classes="wizard-title")
            yield Label("Name:")
            yield Input(placeholder="e.g. Security Auditor", id="agent-name")
            yield Label("Avatar character:")
            yield Input(placeholder="e.g. S", id="agent-avatar", max_length=1)
            yield Label(f"Color: {self._color}")
            yield Button("Next ->", id="next-btn", variant="primary")
            yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "next-btn":
            name_input = self.query_one("#agent-name", Input)
            avatar_input = self.query_one("#agent-avatar", Input)
            self.dismiss({
                "name": name_input.value.strip(),
                "avatar": avatar_input.value.strip() or name_input.value[0:1].upper(),
                "color": self._color,
            })


class AgentMissionScreen(Screen):
    """Step 2/4: Agent mission description."""

    CSS = """
    AgentMissionScreen { align: center middle; }
    #wizard-container { width: 60; height: 20; padding: 2 4; border: round $accent; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static("Step 2/4: Mission", classes="wizard-title")
            yield Label("Describe this agent's mission (1-2 sentences):")
            yield TextArea(id="mission-input")
            yield Button("Next ->", id="next-btn", variant="primary")
            yield Button("<- Back", id="back-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.dismiss(None)
        elif event.button.id == "next-btn":
            text_area = self.query_one("#mission-input", TextArea)
            self.dismiss({"mission": text_area.text.strip()})


class AgentSkillsScreen(Screen):
    """Step 3/4: Select capabilities."""

    CSS = """
    AgentSkillsScreen { align: center middle; }
    #wizard-container { width: 60; padding: 2 4; border: round $accent; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._selected: set[str] = set()

    def compose(self) -> ComposeResult:
        from textual.widgets import Checkbox
        with Vertical(id="wizard-container"):
            yield Static("Step 3/4: Skills & Tools", classes="wizard-title")
            yield Label("Select capabilities:")
            for skill_id, skill_label in AVAILABLE_SKILLS:
                yield Checkbox(skill_label, id=f"skill-{skill_id}")
            yield Button("Next ->", id="next-btn", variant="primary")
            yield Button("<- Back", id="back-btn")

    def on_checkbox_changed(self, event) -> None:
        skill_id = event.checkbox.id.replace("skill-", "")
        if event.value:
            self._selected.add(skill_id)
        else:
            self._selected.discard(skill_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.dismiss(None)
        elif event.button.id == "next-btn":
            self.dismiss({"skills": list(self._selected)})


class AgentConfirmScreen(Screen):
    """Step 4/4: Review and confirm."""

    CSS = """
    AgentConfirmScreen { align: center middle; }
    #wizard-container { width: 60; padding: 2 4; border: round $accent; }
    """

    def __init__(self, agent_data: dict) -> None:
        super().__init__()
        self._data = agent_data

    def compose(self) -> ComposeResult:
        d = self._data
        skill_names = [s[1] for s in AVAILABLE_SKILLS if s[0] in d.get("skills", [])]
        with Vertical(id="wizard-container"):
            yield Static("Step 4/4: Confirm", classes="wizard-title")
            yield Static(
                f"({d.get('avatar', '?')}) {d.get('name', 'Unnamed')}\n"
                f"Mission: {d.get('mission', 'No mission')}\n"
                f"Skills: {', '.join(skill_names) or 'None'}\n"
                f"Scope: This project"
            )
            yield Button("Create Agent", id="create-btn", variant="primary")
            yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "create-btn":
            self.dismiss(self._data)
