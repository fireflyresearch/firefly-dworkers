"""Multi-screen setup wizard for the dworkers TUI.

Guides the user through configuration in 6 steps:
1. Welcome introduction
2. About you (name, role, company)
3. Select an LLM provider (all providers shown, detected ones marked with checkmark)
4. Select a model (models for the chosen provider)
5. Enter API key (only if not already in environment)
6. Configure backend mode + autonomy level

Each step is a separate Textual Screen with keyboard navigation.
"""

from __future__ import annotations

import contextlib
import os

from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, RadioButton, RadioSet, Static

from firefly_dworkers_cli.config import _PROVIDER_ENV_KEYS, ConfigManager

# ── Data ──────────────────────────────────────────────────────────────

_PROVIDER_MODELS: dict[str, list[tuple[str, str]]] = {
    "openai": [
        ("openai:gpt-5.2", "GPT-5.2 (recommended)"),
        ("openai:gpt-5.2-pro", "GPT-5.2 Pro (most capable)"),
        ("openai:o3", "o3 (reasoning)"),
        ("openai:o3-mini", "o3-mini (fast reasoning)"),
    ],
    "anthropic": [
        ("anthropic:claude-opus-4-6", "Claude Opus 4.6 (most capable)"),
        ("anthropic:claude-sonnet-4-5-20250929", "Claude Sonnet 4.5 (recommended)"),
        ("anthropic:claude-haiku-4-5-20251001", "Claude Haiku 4.5 (fastest, cheapest)"),
    ],
    "google": [
        ("google:gemini-3-flash", "Gemini 3 Flash (latest)"),
        ("google:gemini-2.5-pro", "Gemini 2.5 Pro"),
        ("google:gemini-2.5-flash", "Gemini 2.5 Flash"),
    ],
    "mistral": [
        ("mistral:mistral-large-3-25-12", "Mistral Large 3 (latest)"),
        ("mistral:mistral-small-3-2-25-06", "Mistral Small 3.2"),
        ("mistral:devstral-2-25-12", "Devstral 2 (coding)"),
    ],
    "groq": [
        ("groq:llama-3.3-70b-versatile", "Llama 3.3 70B"),
        ("groq:meta-llama/llama-4-maverick-17b-128e-instruct", "Llama 4 Maverick"),
        ("groq:deepseek-r1-distill-llama-70b", "DeepSeek R1 (reasoning)"),
        ("groq:qwen/qwen-3-32b", "Qwen 3 32B"),
    ],
}

_MODE_OPTIONS = [
    ("auto", "Auto-detect", "Try remote server, fall back to local"),
    ("local", "Local", "Run workers in-process (no server needed)"),
    ("remote", "Remote", "Connect to a dworkers server"),
]

_AUTONOMY_OPTIONS = [
    ("semi_supervised", "Semi-supervised (recommended)", "Checkpoints at key decisions"),
    ("manual", "Manual", "Approve every step — maximum oversight"),
    ("autonomous", "Autonomous", "No checkpoints — workers run freely"),
]

ALL_PROVIDERS: list[tuple[str, str]] = [
    ("openai", "OpenAI"),
    ("anthropic", "Anthropic"),
    ("google", "Google"),
    ("mistral", "Mistral"),
    ("groq", "Groq"),
    ("other", "Other (custom model ID)"),
]

# ── Shared CSS ────────────────────────────────────────────────────────

_WIZARD_CSS = """
Screen {
    background: transparent;
    color: #d4d4d4;
}

Middle {
    background: transparent;
    width: 1fr;
    height: 1fr;
}

Center {
    background: transparent;
    width: 1fr;
    height: auto;
}

.wizard-container {
    width: 60;
    height: auto;
    padding: 1 3;
}

.wizard-title {
    text-align: center;
    text-style: bold;
    color: #d4d4d4;
    padding: 1 0 0 0;
    width: 1fr;
}

.wizard-step-indicator {
    text-align: center;
    color: #555555;
    padding: 0 0 1 0;
    width: 1fr;
}

.wizard-subtitle {
    text-align: center;
    color: #666666;
    padding: 0 0 1 0;
    width: 1fr;
}

.wizard-section-title {
    color: #d4d4d4;
    padding: 1 0 0 0;
}

.wizard-hint {
    color: #555555;
    text-style: italic;
}

.wizard-detected {
    color: #10b981;
    text-align: center;
    padding: 0 0 1 0;
    width: 1fr;
}

.wizard-not-detected {
    color: #666666;
}

.wizard-error {
    color: #ef4444;
}

RadioSet {
    background: transparent;
    border: none;
    height: auto;
    width: 1fr;
    padding: 0;
}

RadioSet:focus {
    border: none;
}

RadioButton {
    background: transparent;
    color: #666666;
}

RadioButton:hover {
    color: #d4d4d4;
}

RadioButton.-on {
    color: #ffffff;
    text-style: bold;
}

Input {
    background: transparent;
    border: tall #444444;
    color: #d4d4d4;
    width: 1fr;
    margin: 1 0;
}

Input:focus {
    border: tall #666666;
}

#wizard-actions {
    padding: 1 0 0 0;
    width: 1fr;
    height: auto;
    align: center middle;
}

Button {
    min-width: 20;
    background: transparent;
    color: #d4d4d4;
    border: tall #444444;
}

Button:hover {
    border: tall #666666;
}

Button.-primary {
    background: #d4d4d4;
    color: #000000;
    border: none;
}

Button.-primary:hover {
    background: #e5e5e5;
    color: #000000;
}

.wizard-footer {
    dock: bottom;
    height: 1;
    color: #555555;
    text-align: center;
    width: 1fr;
}
"""


# ── Helper ────────────────────────────────────────────────────────────

def _detect_provider_from_key(key: str) -> str | None:
    """Guess the provider from the API key prefix.

    Returns a provider name or "unknown" for unrecognized formats.
    Keys shorter than 10 characters are rejected (returns None).
    """
    key = key.strip()
    if len(key) < 10:
        return None
    if key.startswith("sk-ant-") or key.startswith("ant-"):
        return "anthropic"
    if key.startswith("sk-"):
        return "openai"
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith("AIza"):
        return "google"
    if key.startswith("mistral-"):
        return "mistral"
    return "unknown"


# ── Screen 1: Welcome ────────────────────────────────────────────────


class WelcomeScreen(Screen):
    """Step 1/6: Welcome introduction."""

    CSS = _WIZARD_CSS
    BINDINGS = [
        ("escape", "quit_wizard", "Quit"),
        ("enter", "confirm", "Continue"),
    ]

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                with Vertical(classes="wizard-container"):
                    yield Static("dworkers", classes="wizard-title")
                    yield Static("step 1 of 6", classes="wizard-step-indicator")
                    yield Static(
                        "Welcome to dworkers — your AI team of\n"
                        "specialized workers ready to help you.\n\n"
                        "Let's get you set up in a few quick steps.",
                        classes="wizard-subtitle",
                    )
                    with Center(id="wizard-actions"):
                        yield Button("Get Started", variant="primary", id="btn-continue")
        yield Static("enter continue  esc skip", classes="wizard-footer")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            self.dismiss(True)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_quit_wizard(self) -> None:
        self.dismiss(None)


# ── Screen 2: About You ─────────────────────────────────────────────


class AboutYouScreen(Screen):
    """Step 2/6: Collect user name, role, company."""

    CSS = _WIZARD_CSS
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._name = ""
        self._role = ""
        self._company = ""

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                with Vertical(classes="wizard-container"):
                    yield Static("dworkers", classes="wizard-title")
                    yield Static("step 2 of 6", classes="wizard-step-indicator")
                    yield Static("Tell us about yourself", classes="wizard-subtitle")

                    yield Static("Your name", classes="wizard-section-title")
                    yield Input(placeholder="e.g., Antonio", id="input-name")

                    yield Static("Your role", classes="wizard-section-title")
                    yield Input(placeholder="e.g., CTO, Product Manager", id="input-role")

                    yield Static("Company", classes="wizard-section-title")
                    yield Input(placeholder="e.g., Firefly Research", id="input-company")

                    with Center(id="wizard-actions"):
                        yield Button("Continue", variant="primary", id="btn-continue")
        yield Static("tab next field  enter continue  esc back", classes="wizard-footer")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            self._submit()

    def _submit(self) -> None:
        with contextlib.suppress(Exception):
            self._name = self.query_one("#input-name", Input).value.strip()
            self._role = self.query_one("#input-role", Input).value.strip()
            self._company = self.query_one("#input-company", Input).value.strip()
        self.dismiss({
            "name": self._name,
            "role": self._role,
            "company": self._company,
        })

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 3: Provider Selection ──────────────────────────────────────

class ProviderScreen(Screen):
    """Step 3/6: Select an LLM provider."""

    CSS = _WIZARD_CSS
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("enter", "confirm", "Confirm"),
    ]

    def __init__(self, detected: dict[str, str]) -> None:
        super().__init__()
        self._detected = detected
        self._selected: str = ALL_PROVIDERS[0][0]  # default to first

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                with Vertical(classes="wizard-container"):
                    yield Static("dworkers", classes="wizard-title")
                    yield Static("step 3 of 6", classes="wizard-step-indicator")
                    yield Static("Select your LLM provider", classes="wizard-subtitle")

                    if self._detected:
                        names = ", ".join(p.title() for p in sorted(self._detected))
                        yield Static(f"Detected: {names}", classes="wizard-detected")

                    with RadioSet(id="provider-select", classes="wizard-radio-set"):
                        for i, (provider_id, display_name) in enumerate(ALL_PROVIDERS):
                            suffix = ""
                            if provider_id in self._detected:
                                suffix = " (detected)"
                            yield RadioButton(
                                f"{display_name}{suffix}",
                                value=i == 0,
                                name=provider_id,
                            )

                    with Center(id="wizard-actions"):
                        yield Button("Continue", variant="primary", id="btn-continue")

        yield Static(
            "up/down navigate  enter confirm  esc back",
            classes="wizard-footer",
        )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed.name:
            self._selected = event.pressed.name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            self.dismiss(self._selected)

    def action_confirm(self) -> None:
        self.dismiss(self._selected)

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 4: Model Selection ─────────────────────────────────────────

class ModelScreen(Screen):
    """Step 4/6: Select a model for the chosen provider."""

    CSS = _WIZARD_CSS
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("enter", "confirm", "Confirm"),
    ]

    def __init__(self, provider: str) -> None:
        super().__init__()
        self._provider = provider
        models = _PROVIDER_MODELS.get(provider, [])
        self._selected: str = models[0][0] if models else ""
        self._custom_mode: bool = not models

    def compose(self) -> ComposeResult:
        models = _PROVIDER_MODELS.get(self._provider, [])
        provider_name = dict(ALL_PROVIDERS).get(self._provider, self._provider)

        with Middle():
            with Center():
                with Vertical(classes="wizard-container"):
                    yield Static("dworkers", classes="wizard-title")
                    yield Static("step 4 of 6", classes="wizard-step-indicator")
                    yield Static(
                        f"Select a model  {provider_name}",
                        classes="wizard-subtitle",
                    )

                    if models:
                        with RadioSet(id="model-select", classes="wizard-radio-set"):
                            for i, (model_id, label) in enumerate(models):
                                yield RadioButton(label, value=i == 0, name=model_id)
                            yield RadioButton(
                                "Custom model ID",
                                value=False,
                                name="_custom",
                            )
                    else:
                        yield Static(
                            "Enter your model ID (provider:model-name):",
                            classes="wizard-hint",
                        )
                        yield Input(
                            placeholder="e.g., openai:gpt-5.2",
                            id="custom-model-input",
                            classes="wizard-input",
                        )

                    with Center(id="wizard-actions"):
                        yield Button("Continue", variant="primary", id="btn-continue")

        yield Static(
            "up/down navigate  enter confirm  esc back",
            classes="wizard-footer",
        )

    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed.name == "_custom":
            self._custom_mode = True
            await self._show_custom_input()
        elif event.pressed.name:
            self._selected = event.pressed.name

    async def _show_custom_input(self) -> None:
        """Replace the radio set with a text input for custom model."""
        try:
            container = self.query_one(".wizard-container")
            radio = self.query_one("#model-select")
            await radio.remove()
            input_widget = Input(
                placeholder=f"e.g., {self._provider}:model-name",
                id="custom-model-input",
                classes="wizard-input",
            )
            actions = self.query_one("#wizard-actions")
            await container.mount(input_widget, before=actions)
            input_widget.focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "custom-model-input":
            self._submit()

    def _submit(self) -> None:
        if self._custom_mode:
            try:
                value = self.query_one("#custom-model-input", Input).value.strip()
                if value:
                    self.dismiss(value)
            except Exception:
                pass
        elif self._selected:
            self.dismiss(self._selected)

    def action_confirm(self) -> None:
        self._submit()

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 5: API Key Entry ───────────────────────────────────────────

class ApiKeyScreen(Screen):
    """Step 5/6: Enter API key for the selected provider."""

    CSS = _WIZARD_CSS
    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, provider: str) -> None:
        super().__init__()
        self._provider = provider

    def compose(self) -> ComposeResult:
        env_var = _PROVIDER_ENV_KEYS.get(self._provider, "API_KEY")
        provider_name = dict(ALL_PROVIDERS).get(self._provider, self._provider)

        with Middle():
            with Center():
                with Vertical(classes="wizard-container"):
                    yield Static("dworkers", classes="wizard-title")
                    yield Static("step 5 of 6", classes="wizard-step-indicator")
                    yield Static("Enter your API key", classes="wizard-subtitle")

                    yield Static(
                        f"Enter your {provider_name} API key to get started:",
                        classes="wizard-hint",
                    )
                    yield Input(
                        placeholder="sk-... or ant-...",
                        password=True,
                        id="api-key-input",
                        classes="wizard-input",
                    )
                    yield Static("", id="api-key-error", classes="wizard-error")

                    with Center(id="wizard-actions"):
                        yield Button("Continue", variant="primary", id="btn-continue")

        yield Static(
            "enter confirm  esc back",
            classes="wizard-footer",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            self._submit_key()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self._submit_key()

    def _submit_key(self) -> None:
        try:
            key = self.query_one("#api-key-input", Input).value.strip()
        except Exception:
            return
        if not key:
            self._show_error("Please enter an API key.")
            return
        detected = _detect_provider_from_key(key)
        if detected is None:
            self._show_error("Key is too short. Please check and try again.")
            return
        self.dismiss(key)

    def _show_error(self, message: str) -> None:
        with contextlib.suppress(Exception):
            self.query_one("#api-key-error", Static).update(message)

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 6: Mode + Autonomy ─────────────────────────────────────────

class ConfigScreen(Screen):
    """Step 6/6: Configure backend mode and autonomy level."""

    CSS = _WIZARD_CSS
    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._selected_mode = "auto"
        self._selected_autonomy = "semi_supervised"

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                with Vertical(classes="wizard-container"):
                    yield Static("dworkers", classes="wizard-title")
                    yield Static("step 6 of 6", classes="wizard-step-indicator")
                    yield Static("Configuration", classes="wizard-subtitle")

                    yield Static("Backend mode", classes="wizard-section-title")
                    with RadioSet(id="mode-select", classes="wizard-radio-set"):
                        for i, (mode_id, label, desc) in enumerate(_MODE_OPTIONS):
                            yield RadioButton(
                                f"{label} -- {desc}",
                                value=i == 0,
                                name=mode_id,
                            )

                    yield Static("Autonomy level", classes="wizard-section-title")
                    with RadioSet(id="autonomy-select", classes="wizard-radio-set"):
                        for i, (autonomy_id, label, desc) in enumerate(_AUTONOMY_OPTIONS):
                            yield RadioButton(
                                f"{label} -- {desc}",
                                value=i == 0,
                                name=autonomy_id,
                            )

                    with Center(id="wizard-actions"):
                        yield Button("Save & Start", variant="primary", id="btn-save")

        yield Static(
            "up/down navigate  tab switch section  enter save  esc back",
            classes="wizard-footer",
        )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed.name:
            if event.radio_set.id == "mode-select":
                self._selected_mode = event.pressed.name
            elif event.radio_set.id == "autonomy-select":
                self._selected_autonomy = event.pressed.name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.dismiss((self._selected_mode, self._selected_autonomy))

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 7: Meet the Team ──────────────────────────────────────────


class MeetTheTeamScreen(Screen):
    """Final screen: introduce the AI team to the user."""

    CSS = _WIZARD_CSS
    BINDINGS = [("enter", "confirm", "Start")]

    def __init__(self, user_name: str = "") -> None:
        super().__init__()
        self._user_name = user_name

    def compose(self) -> ComposeResult:
        greeting = f"Welcome{', ' + self._user_name if self._user_name else ''}!"
        team_text = (
            f"{greeting} Meet your AI team:\n\n"
            "(A) Amara  Manager\n"
            "    Your team lead — routes tasks and launches plans\n\n"
            "(L) Leo  Analyst\n"
            "    Strategic analysis and actionable recommendations\n\n"
            "(Y) Yuki  Researcher\n"
            "    Deep research and knowledge synthesis\n\n"
            "(K) Kofi  Data Analyst\n"
            "    Data processing, queries, and visualization\n\n"
            "(N) Noor  Designer\n"
            "    Document design and creative work"
        )
        with Middle():
            with Center():
                with Vertical(classes="wizard-container"):
                    yield Static("dworkers", classes="wizard-title")
                    yield Static("Your team is ready", classes="wizard-subtitle")
                    yield Static(team_text, classes="wizard-hint")
                    with Center(id="wizard-actions"):
                        yield Button("Start chatting", variant="primary", id="btn-start")
        yield Static("enter start", classes="wizard-footer")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start":
            self.dismiss(True)

    def action_confirm(self) -> None:
        self.dismiss(True)


# ── Wizard Controller ─────────────────────────────────────────────────

class SetupWizard(Screen):
    """Multi-screen setup wizard controller.

    Orchestrates the 6-step flow:
    Welcome -> About You -> Provider -> Model -> API Key -> Config.
    Pushed onto the app's screen stack by DworkersApp.on_mount().
    """

    CSS = _WIZARD_CSS

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        super().__init__()
        self._config_mgr = config_manager or ConfigManager()
        self._detected: dict[str, str] = {}
        self._user_profile: dict[str, str] = {}
        self._selected_provider: str = ""
        self._selected_model: str = ""
        self._api_key: str = ""
        self._selected_mode: str = "auto"
        self._selected_autonomy: str = "semi_supervised"

    def compose(self) -> ComposeResult:
        yield Static("")

    def on_mount(self) -> None:
        self._detected = self._config_mgr.detect_api_keys()
        self._push_welcome()

    # ── Step 1: Welcome ──────────────────────────────────────────────

    def _push_welcome(self) -> None:
        """Step 1: Welcome introduction."""
        self.app.push_screen(WelcomeScreen(), callback=self._on_welcome)

    def _on_welcome(self, result: object) -> None:
        if result is None:
            self._skip()
            return
        self._push_about_you()

    # ── Step 2: About You ────────────────────────────────────────────

    def _push_about_you(self) -> None:
        """Step 2: Collect user name, role, company."""
        self.app.push_screen(AboutYouScreen(), callback=self._on_about_you)

    def _on_about_you(self, result: object) -> None:
        if result is None:
            self._push_welcome()
            return
        if isinstance(result, dict):
            self._user_profile = result
        self._push_provider()

    # ── Step 3: Provider ─────────────────────────────────────────────

    def _push_provider(self) -> None:
        """Step 3: Provider selection."""
        self.app.push_screen(
            ProviderScreen(self._detected), callback=self._on_provider
        )

    def _on_provider(self, result: object) -> None:
        if result is None:
            self._push_about_you()
            return
        self._selected_provider = str(result)
        self._push_model()

    # ── Step 4: Model ────────────────────────────────────────────────

    def _push_model(self) -> None:
        """Step 4: Model selection."""
        self.app.push_screen(
            ModelScreen(self._selected_provider), callback=self._on_model
        )

    def _on_model(self, result: object) -> None:
        if result is None:
            self._push_provider()
            return
        self._selected_model = str(result)
        self._push_api_key()

    # ── Step 5: API Key ──────────────────────────────────────────────

    def _push_api_key(self) -> None:
        """Step 5: API key (conditional)."""
        provider = self._selected_provider
        if provider in self._detected or provider == "other":
            self._push_config()
            return
        self.app.push_screen(
            ApiKeyScreen(provider), callback=self._on_api_key
        )

    def _on_api_key(self, result: object) -> None:
        if result is None:
            self._push_model()
            return
        self._api_key = str(result)
        env_key = _PROVIDER_ENV_KEYS.get(self._selected_provider, "")
        if env_key:
            os.environ[env_key] = self._api_key
        self._push_config()

    # ── Step 6: Config ───────────────────────────────────────────────

    def _push_config(self) -> None:
        """Step 6: Mode + Autonomy."""
        self.app.push_screen(ConfigScreen(), callback=self._on_config)

    def _on_config(self, result: object) -> None:
        if result is None:
            self._push_api_key()
            return
        mode, autonomy = result  # type: ignore[misc]
        self._selected_mode = str(mode)
        self._selected_autonomy = str(autonomy)
        self._save_and_finish()

    # ── Save & Finish ────────────────────────────────────────────────

    def _save_and_finish(self) -> None:
        """Save config and show Meet the Team screen."""
        model = self._selected_model or "openai:gpt-5.2"
        config_data = self._config_mgr.build_default_config(
            model=model,
            mode=self._selected_mode,
            default_autonomy=self._selected_autonomy,
            user_name=self._user_profile.get("name", ""),
            user_role=self._user_profile.get("role", ""),
            user_company=self._user_profile.get("company", ""),
        )
        self._config_mgr.save_global(config_data)
        user_name = self._user_profile.get("name", "")
        self.app.push_screen(
            MeetTheTeamScreen(user_name=user_name),
            callback=self._on_meet_team,
        )

    def _on_meet_team(self, result: object) -> None:
        """Callback after Meet the Team screen dismisses."""
        try:
            config = self._config_mgr.load()
            self.dismiss(config)
        except Exception:
            self.dismiss(None)

    def _skip(self) -> None:
        """Skip setup with defaults."""
        config_data = self._config_mgr.build_default_config()
        self._config_mgr.save_global(config_data)
        try:
            config = self._config_mgr.load()
            self.dismiss(config)
        except Exception:
            self.dismiss(None)
