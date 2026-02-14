"""Multi-screen setup wizard for the dworkers TUI.

Guides the user through configuration in 4 steps:
1. Select an LLM provider (all providers shown, detected ones marked with checkmark)
2. Select a model (models for the chosen provider)
3. Enter API key (only if not already in environment)
4. Configure backend mode + autonomy level

Each step is a separate Textual Screen with keyboard navigation.
"""

from __future__ import annotations

import contextlib
import os

from textual.app import ComposeResult
from textual.containers import Center, VerticalScroll
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
    background: #000000;
    color: #d4d4d4;
}

.wizard-container {
    width: 60;
    height: auto;
    max-height: 90%;
    padding: 1 2;
}

.wizard-title {
    text-align: center;
    color: #d4d4d4;
    padding: 1 0;
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
    padding: 0 0 0 2;
    text-style: italic;
}

.wizard-detected {
    color: #10b981;
    padding: 0 0 0 2;
}

.wizard-not-detected {
    color: #666666;
    padding: 0 0 0 2;
}

.wizard-error {
    color: #ef4444;
    padding: 0 0 0 2;
}

.wizard-radio-set {
    padding: 0 0 0 2;
    height: auto;
    width: 1fr;
}

.wizard-input {
    margin: 0 2;
    width: 1fr;
    background: #000000;
    border: tall #333333;
    color: #d4d4d4;
}

.wizard-footer {
    dock: bottom;
    height: 1;
    background: #000000;
    color: #555555;
    padding: 0 2;
    text-align: center;
    width: 1fr;
}

.wizard-step-indicator {
    text-align: center;
    color: #555555;
    padding: 0 0 1 0;
    width: 1fr;
}

#wizard-actions {
    padding: 1 0;
    width: 1fr;
    height: auto;
    align: center middle;
}

Button {
    min-width: 16;
    background: #000000;
    color: #d4d4d4;
    border: tall #333333;
}

Button:hover {
    background: #111111;
}

Button.-primary {
    border: tall #d4d4d4;
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


# ── Screen 1: Provider Selection ──────────────────────────────────────

class ProviderScreen(Screen):
    """Select an LLM provider."""

    CSS = _WIZARD_CSS
    BINDINGS = [("escape", "quit_wizard", "Quit")]

    def __init__(self, detected: dict[str, str]) -> None:
        super().__init__()
        self._detected = detected

    def compose(self) -> ComposeResult:
        with Center(), VerticalScroll(classes="wizard-container"):
            yield Static("dworkers", classes="wizard-title")
            yield Static("step 1 of 4", classes="wizard-step-indicator")
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

            yield Static(
                "up/down navigate  enter select  esc quit",
                classes="wizard-footer",
            )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed.name:
            self.dismiss(event.pressed.name)

    def action_quit_wizard(self) -> None:
        self.dismiss(None)


# ── Screen 2: Model Selection ─────────────────────────────────────────

class ModelScreen(Screen):
    """Select a model for the chosen provider."""

    CSS = _WIZARD_CSS
    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, provider: str) -> None:
        super().__init__()
        self._provider = provider

    def compose(self) -> ComposeResult:
        models = _PROVIDER_MODELS.get(self._provider, [])
        provider_name = dict(ALL_PROVIDERS).get(self._provider, self._provider)

        with Center(), VerticalScroll(classes="wizard-container"):
            yield Static("dworkers", classes="wizard-title")
            yield Static("step 2 of 4", classes="wizard-step-indicator")
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
                "up/down navigate  enter select  esc back",
                classes="wizard-footer",
            )

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed.name == "_custom":
            self._show_custom_input()
        elif event.pressed.name:
            self.dismiss(event.pressed.name)

    def _show_custom_input(self) -> None:
        """Replace the radio set with a text input for custom model."""
        try:
            container = self.query_one(".wizard-container")
            radio = self.query_one("#model-select")
            radio.remove()
            input_widget = Input(
                placeholder=f"e.g., {self._provider}:model-name",
                id="custom-model-input",
                classes="wizard-input",
            )
            container.mount(input_widget, before=self.query_one(".wizard-footer"))
            btn = Button("Continue", variant="primary", id="btn-continue")
            center = Center(id="wizard-actions")
            container.mount(center, before=self.query_one(".wizard-footer"))
            center.mount(btn)
            input_widget.focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            try:
                value = self.query_one("#custom-model-input", Input).value.strip()
                if value:
                    self.dismiss(value)
            except Exception:
                pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "custom-model-input":
            value = event.value.strip()
            if value:
                self.dismiss(value)

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 3: API Key Entry ───────────────────────────────────────────

class ApiKeyScreen(Screen):
    """Enter API key for the selected provider."""

    CSS = _WIZARD_CSS
    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, provider: str) -> None:
        super().__init__()
        self._provider = provider

    def compose(self) -> ComposeResult:
        env_var = _PROVIDER_ENV_KEYS.get(self._provider, "API_KEY")
        provider_name = dict(ALL_PROVIDERS).get(self._provider, self._provider)

        with Center(), VerticalScroll(classes="wizard-container"):
            yield Static("dworkers", classes="wizard-title")
            yield Static("step 3 of 4", classes="wizard-step-indicator")
            yield Static("Enter your API key", classes="wizard-subtitle")

            yield Static(
                f"{env_var} not found in environment",
                classes="wizard-not-detected",
            )
            yield Static(
                f"Enter your {provider_name} API key:",
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


# ── Screen 4: Mode + Autonomy ─────────────────────────────────────────

class ConfigScreen(Screen):
    """Configure backend mode and autonomy level."""

    CSS = _WIZARD_CSS
    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self) -> None:
        super().__init__()
        self._selected_mode = "auto"
        self._selected_autonomy = "semi_supervised"

    def compose(self) -> ComposeResult:
        with Center(), VerticalScroll(classes="wizard-container"):
            yield Static("dworkers", classes="wizard-title")
            yield Static("step 4 of 4", classes="wizard-step-indicator")
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


# ── Wizard Controller ─────────────────────────────────────────────────

class SetupWizard(Screen):
    """Multi-screen setup wizard controller.

    Orchestrates the 4-step flow: Provider -> Model -> API Key -> Config.
    Pushed onto the app's screen stack by DworkersApp.on_mount().
    """

    CSS = _WIZARD_CSS

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        super().__init__()
        self._config_mgr = config_manager or ConfigManager()
        self._detected: dict[str, str] = {}
        self._selected_provider: str = ""
        self._selected_model: str = ""
        self._api_key: str = ""
        self._selected_mode: str = "auto"
        self._selected_autonomy: str = "semi_supervised"

    def compose(self) -> ComposeResult:
        yield Static("")

    async def on_mount(self) -> None:
        self._detected = self._config_mgr.detect_api_keys()
        await self._step_provider()

    async def _step_provider(self) -> None:
        """Step 1: Provider selection."""
        result = await self.app.push_screen_wait(ProviderScreen(self._detected))
        if result is None:
            self._skip()
            return
        self._selected_provider = result
        await self._step_model()

    async def _step_model(self) -> None:
        """Step 2: Model selection."""
        result = await self.app.push_screen_wait(ModelScreen(self._selected_provider))
        if result is None:
            await self._step_provider()
            return
        self._selected_model = result
        await self._step_api_key()

    async def _step_api_key(self) -> None:
        """Step 3: API key (conditional)."""
        provider = self._selected_provider
        if provider in self._detected or provider == "other":
            await self._step_config()
            return

        result = await self.app.push_screen_wait(ApiKeyScreen(provider))
        if result is None:
            await self._step_model()
            return
        self._api_key = result
        env_key = _PROVIDER_ENV_KEYS.get(provider, "")
        if env_key:
            os.environ[env_key] = self._api_key
        await self._step_config()

    async def _step_config(self) -> None:
        """Step 4: Mode + Autonomy."""
        result = await self.app.push_screen_wait(ConfigScreen())
        if result is None:
            await self._step_api_key()
            return
        self._selected_mode, self._selected_autonomy = result
        self._save_and_finish()

    def _save_and_finish(self) -> None:
        """Save config and dismiss."""
        model = self._selected_model or "openai:gpt-5.2"
        config_data = self._config_mgr.build_default_config(
            model=model,
            mode=self._selected_mode,
            default_autonomy=self._selected_autonomy,
        )
        self._config_mgr.save_global(config_data)
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
