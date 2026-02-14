"""First-run setup wizard for the dworkers TUI.

Launches when no usable configuration exists. Guides the user through:
1. Detecting available LLM provider API keys from environment
2. Choosing a default model
3. Selecting a backend mode (auto / local / remote)
4. Choosing an autonomy level (semi-supervised / manual / autonomous)
5. Optionally configuring messaging integrations (Slack, Teams)
6. Saving the configuration globally (~/.dworkers/config.yaml)

The wizard uses Textual widgets for a clean terminal UI experience.
"""

from __future__ import annotations

import os

from textual.app import ComposeResult
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from firefly_dworkers_cli.config import _PROVIDER_ENV_KEYS, ConfigManager

# Model choices per provider — updated February 2026
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

_SETUP_CSS = """
SetupScreen {
    background: #1a1a2e;
    color: #e2e8f0;
}

#setup-container {
    width: 80;
    height: auto;
    max-height: 90%;
    padding: 1 2;
}

.setup-title {
    text-align: center;
    text-style: bold;
    color: #6366f1;
    padding: 1 0;
    width: 1fr;
}

.setup-subtitle {
    text-align: center;
    color: #64748b;
    padding: 0 0 1 0;
    width: 1fr;
}

.setup-section {
    padding: 1 0;
    width: 1fr;
}

.setup-section-title {
    text-style: bold;
    color: #10b981;
    padding: 0 0 1 0;
}

.setup-label {
    color: #94a3b8;
    padding: 0 0 0 2;
}

.setup-detected {
    color: #10b981;
    padding: 0 0 0 2;
}

.setup-not-detected {
    color: #f59e0b;
    padding: 0 0 0 2;
}

.setup-error {
    color: #ef4444;
    padding: 0 0 0 2;
}

.setup-hint {
    color: #475569;
    padding: 0 0 0 2;
    text-style: italic;
}

.setup-radio-set {
    padding: 0 0 0 2;
    height: auto;
    width: 1fr;
}

.setup-input {
    margin: 0 2;
    width: 1fr;
}

#setup-actions {
    padding: 1 0;
    width: 1fr;
    height: auto;
    align: center middle;
}

#btn-save {
    margin: 0 1;
}

#btn-skip {
    margin: 0 1;
}

Button {
    min-width: 16;
}
"""


class SetupScreen(Screen):
    """First-run setup wizard screen."""

    CSS = _SETUP_CSS
    BINDINGS = [("escape", "skip", "Skip Setup")]

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        super().__init__()
        self._config_mgr = config_manager or ConfigManager()
        self._detected_providers: dict[str, str] = {}
        self._selected_model: str = ""
        self._selected_mode: str = ""
        self._selected_autonomy: str = ""
        self._manual_api_key: str = ""
        self._manual_provider: str = ""

    def compose(self) -> ComposeResult:
        self._detected_providers = self._config_mgr.detect_api_keys()

        with Center(), VerticalScroll(id="setup-container"):
            yield Static("dworkers", classes="setup-title")
            yield Static(
                "Digital Workers as a Service — First-Run Setup",
                classes="setup-subtitle",
            )

            # Step 1: API key detection
            with Vertical(classes="setup-section"):
                yield Static(
                    "Step 1: LLM Provider", classes="setup-section-title"
                )

                if self._detected_providers:
                    providers = ", ".join(
                        p.title() for p in sorted(self._detected_providers)
                    )
                    yield Static(
                        f"Detected API keys: {providers}",
                        classes="setup-detected",
                    )
                else:
                    yield Static(
                        "No API keys detected in environment.",
                        classes="setup-not-detected",
                    )
                    yield Static(
                        "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, etc. in your shell, "
                        "or enter one below.",
                        classes="setup-hint",
                    )

                # Manual API key entry
                yield Static(
                    "Or enter an API key manually:",
                    classes="setup-label",
                )
                yield Input(
                    placeholder="sk-... or ant-...",
                    password=True,
                    id="api-key-input",
                    classes="setup-input",
                )

            # Step 2: Model selection
            with Vertical(classes="setup-section"):
                yield Static(
                    "Step 2: Default Model", classes="setup-section-title"
                )

                # Build radio buttons for available models
                available_models = self._get_available_models()
                if available_models:
                    with RadioSet(id="model-select", classes="setup-radio-set"):
                        for i, (model_id, label) in enumerate(available_models):
                            yield RadioButton(
                                label, value=i == 0, name=model_id
                            )
                    self._selected_model = available_models[0][0]
                else:
                    yield Static(
                        "Enter an API key above to see available models.",
                        classes="setup-hint",
                    )
                    yield Input(
                        placeholder="e.g., openai:gpt-5.2",
                        id="model-input",
                        classes="setup-input",
                    )

            # Step 3: Backend mode
            with Vertical(classes="setup-section"):
                yield Static(
                    "Step 3: Backend Mode", classes="setup-section-title"
                )
                with RadioSet(id="mode-select", classes="setup-radio-set"):
                    for i, (mode_id, label, description) in enumerate(
                        _MODE_OPTIONS
                    ):
                        yield RadioButton(
                            f"{label} — {description}",
                            value=i == 0,
                            name=mode_id,
                        )
                self._selected_mode = _MODE_OPTIONS[0][0]

            # Step 4: Autonomy level
            with Vertical(classes="setup-section"):
                yield Static(
                    "Step 4: Autonomy Level", classes="setup-section-title"
                )
                with RadioSet(
                    id="autonomy-select", classes="setup-radio-set"
                ):
                    for i, (autonomy_id, label, description) in enumerate(
                        _AUTONOMY_OPTIONS
                    ):
                        yield RadioButton(
                            f"{label} — {description}",
                            value=i == 0,
                            name=autonomy_id,
                        )
                self._selected_autonomy = _AUTONOMY_OPTIONS[0][0]

            # Step 5: Optional integrations
            with Vertical(classes="setup-section"):
                yield Static(
                    "Step 5: Integrations (optional)",
                    classes="setup-section-title",
                )
                yield Static(
                    "You can configure Slack, Teams, and other integrations later "
                    "using /connectors and /setup in the chat.",
                    classes="setup-hint",
                )

            # Actions
            with Center(id="setup-actions"):
                yield Button(
                    "Save & Start",
                    variant="primary",
                    id="btn-save",
                )
                yield Button(
                    "Skip (use defaults)",
                    variant="default",
                    id="btn-skip",
                )

    def _get_available_models(self) -> list[tuple[str, str]]:
        """Return model choices for detected providers."""
        models: list[tuple[str, str]] = []
        for provider in sorted(self._detected_providers):
            provider_models = _PROVIDER_MODELS.get(provider, [])
            models.extend(provider_models)
        return models

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Track the selected model, mode, or autonomy level."""
        button = event.pressed
        radio_set_id = event.radio_set.id
        if button.name:
            if radio_set_id == "model-select":
                self._selected_model = button.name
            elif radio_set_id == "mode-select":
                self._selected_mode = button.name
            elif radio_set_id == "autonomy-select":
                self._selected_autonomy = button.name

    def on_input_changed(self, event: Input.Changed) -> None:
        """Track manual API key or model input."""
        if event.input.id == "api-key-input":
            self._manual_api_key = event.value
        elif event.input.id == "model-input":
            self._selected_model = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle save or skip."""
        if event.button.id == "btn-save":
            self._save_config()
        elif event.button.id == "btn-skip":
            self._skip_setup()

    def _save_config(self) -> None:
        """Save configuration and dismiss the setup screen."""
        # Validate: need either detected providers or a valid manual key
        if self._manual_api_key:
            provider = self._detect_provider_from_key(self._manual_api_key)
            if provider is None:
                self._show_error("API key seems too short. Please check and try again.")
                return
        elif not self._detected_providers:
            self._show_error(
                "No API keys detected. Please enter an API key or set one in your environment."
            )
            return

        # Determine model
        model = self._selected_model or "openai:gpt-5.2"

        # If manual API key was entered, detect provider and set env var
        if self._manual_api_key:
            provider = self._detect_provider_from_key(self._manual_api_key)
            if provider and provider != "unknown":
                env_key = _PROVIDER_ENV_KEYS.get(provider, "")
                if env_key:
                    os.environ[env_key] = self._manual_api_key
                    self._detected_providers[provider] = self._manual_api_key
                if not self._selected_model:
                    provider_models = _PROVIDER_MODELS.get(provider, [])
                    if provider_models:
                        model = provider_models[0][0]

        config_data = self._config_mgr.build_default_config(
            model=model,
            mode=self._selected_mode or "auto",
            default_autonomy=self._selected_autonomy or "semi_supervised",
        )
        self._config_mgr.save_global(config_data)

        # Load and register
        config = self._config_mgr.load()
        self.dismiss(config)

    def _show_error(self, message: str) -> None:
        """Display a validation error on the setup screen."""
        try:
            error_label = self.query_one("#setup-error", Label)
            error_label.update(message)
            error_label.display = True
        except Exception:
            # Error label doesn't exist yet — mount one
            container = self.query_one("#setup-container")
            label = Label(message, id="setup-error", classes="setup-error")
            container.mount(label, before=self.query_one("#setup-actions"))

    def _skip_setup(self) -> None:
        """Skip setup, create a minimal default config."""
        config_data = self._config_mgr.build_default_config()
        self._config_mgr.save_global(config_data)
        try:
            config = self._config_mgr.load()
            self.dismiss(config)
        except Exception:
            self.dismiss(None)

    def action_skip(self) -> None:
        """Handle escape key to skip setup."""
        self._skip_setup()

    @staticmethod
    def _detect_provider_from_key(key: str) -> str | None:
        """Guess the provider from the API key prefix.

        Returns a provider name or "unknown" for unrecognized formats.
        Keys shorter than 10 characters are rejected (returns None).
        """
        key = key.strip()
        if len(key) < 10:
            return None
        # Anthropic check before OpenAI since sk-ant- starts with sk-
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
        # Accept unknown key formats gracefully
        return "unknown"
