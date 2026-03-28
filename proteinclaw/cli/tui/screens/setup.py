from __future__ import annotations

import proteinclaw.core.config as config_mod
from proteinclaw.core.config import SUPPORTED_MODELS
from proteinclaw.cli.tui.screens.main import MainScreen  # noqa: PLC0415

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Input, Label, Select


# (provider_id, display_name, env_key)  — env_key is "" for Ollama
_PROVIDERS: list[tuple[str, str, str]] = [
    ("anthropic", "Anthropic",                        "ANTHROPIC_API_KEY"),
    ("openai",    "OpenAI",                           "OPENAI_API_KEY"),
    ("deepseek",  "DeepSeek",                         "DEEPSEEK_API_KEY"),
    ("minimax",   "MiniMax",                          "MINIMAX_API_KEY"),
    ("ollama",    "Ollama (local, no API key needed)", ""),
]


# Providers that reuse another provider's SDK in SUPPORTED_MODELS but are distinct in the wizard
_PROVIDER_MODELS_OVERRIDE: dict[str, list[str]] = {
    "minimax": ["minimax-text-01"],
}


def _models_for_provider(provider: str) -> list[str]:
    if provider in _PROVIDER_MODELS_OVERRIDE:
        return _PROVIDER_MODELS_OVERRIDE[provider]
    return [m for m, cfg in SUPPORTED_MODELS.items() if cfg["provider"] == provider]


class SetupScreen(Screen):
    """Three-step first-run wizard: provider → API key → model."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #setup-container {
        width: 64;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }
    #step-label {
        margin: 1 0 0 0;
        color: $text-muted;
    }
    #hint-label {
        color: $text-muted;
        margin: 0 0 1 0;
    }
    Input {
        margin: 0 0 1 0;
    }
    Select {
        margin: 0 0 1 0;
    }
    """

    current_step: reactive[int] = reactive(1, init=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_provider: str = ""
        self._api_key: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-container"):
            yield Label("Welcome to ProteinClaw!\n")
            yield Label("", id="step-label")
            yield Vertical(id="step-content")
            yield Label("", id="hint-label")

    async def on_mount(self) -> None:
        await self._render_step()

    async def watch_current_step(self, step: int) -> None:  # noqa: ARG002
        await self._render_step()

    async def _render_step(self) -> None:
        step = self.current_step
        content = self.query_one("#step-content", Vertical)
        step_label = self.query_one("#step-label", Label)
        hint_label = self.query_one("#hint-label", Label)

        await content.remove_children()

        if step == 1:
            step_label.update("Step 1 / 3 — Choose your LLM provider")
            hint_label.update("")
            options = [(display, pid) for pid, display, _ in _PROVIDERS]
            select: Select[str] = Select(options, id="provider-select")
            await content.mount(select)
            select.focus()

        elif step == 2:
            _, display_name, _ = next(p for p in _PROVIDERS if p[0] == self._selected_provider)
            step_label.update(f"Step 2 / 3 — {display_name} API Key")
            hint_label.update("Press Enter to continue, Escape to skip")
            inp = Input(placeholder="Paste your API key here", password=True, id="api-key-input")
            await content.mount(inp)
            inp.focus()

        elif step == 3:
            step_label.update("Step 3 / 3 — Default model")
            hint_label.update("Select a model to continue")
            models = _models_for_provider(self._selected_provider)
            options = [(m, m) for m in models]
            select = Select(options, id="model-select")
            await content.mount(select)
            select.focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            return

        if event.select.id == "provider-select":
            self._selected_provider = str(event.value)
            # Ollama needs no API key — jump straight to model selection
            self.current_step = 3 if self._selected_provider == "ollama" else 2

        elif event.select.id == "model-select":
            self._finish(str(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self._api_key = event.value.strip()
            self.current_step = 3

    def on_key(self, event) -> None:  # type: ignore[override]
        focused = self.focused
        if event.key == "escape" and getattr(focused, "id", None) == "api-key-input":
            self._api_key = ""
            self.current_step = 3

    def _finish(self, model: str) -> None:
        keys: dict[str, str] = {}
        if self._api_key and self._selected_provider != "ollama":
            _, _, env_key = next(p for p in _PROVIDERS if p[0] == self._selected_provider)
            if env_key:
                keys[env_key] = self._api_key

        config_mod.save_user_config(keys, model)
        config_mod.load_user_config()

        self.app.switch_screen(MainScreen())
