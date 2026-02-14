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
from textual.containers import Center, Vertical
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
    align: center middle;
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


# ── Screen 1: Provider Selection ──────────────────────────────────────

class ProviderScreen(Screen):
    """Select an LLM provider."""

    CSS = _WIZARD_CSS
    BINDINGS = [("escape", "quit_wizard", "Quit")]

    def __init__(self, detected: dict[str, str]) -> None:
        super().__init__()
        self._detected = detected

    def compose(self) -> ComposeResult:
        with Vertical(classes="wizard-container"):
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

        with Vertical(classes="wizard-container"):
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
            container.mount(input_widget)
            center = Center(id="wizard-actions")
            container.mount(center)
            btn = Button("Continue", variant="primary", id="btn-continue")
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

        with Vertical(classes="wizard-container"):
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
        with Vertical(classes="wizard-container"):
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

    def on_mount(self) -> None:
        self._detected = self._config_mgr.detect_api_keys()
        self._push_provider()

    def _push_provider(self) -> None:
        """Step 1: Provider selection."""
        self.app.push_screen(
            ProviderScreen(self._detected), callback=self._on_provider
        )

    def _on_provider(self, result: object) -> None:
        if result is None:
            self._skip()
            return
        self._selected_provider = str(result)
        self._push_model()

    def _push_model(self) -> None:
        """Step 2: Model selection."""
        self.app.push_screen(
            ModelScreen(self._selected_provider), callback=self._on_model
        )

    def _on_model(self, result: object) -> None:
        if result is None:
            self._push_provider()
            return
        self._selected_model = str(result)
        self._push_api_key()

    def _push_api_key(self) -> None:
        """Step 3: API key (conditional)."""
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

    def _push_config(self) -> None:
        """Step 4: Mode + Autonomy."""
        self.app.push_screen(ConfigScreen(), callback=self._on_config)

    def _on_config(self, result: object) -> None:
        if result is None:
            self._push_api_key()
            return
        mode, autonomy = result  # type: ignore[misc]
        self._selected_mode = str(mode)
        self._selected_autonomy = str(autonomy)
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
