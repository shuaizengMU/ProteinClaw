from __future__ import annotations

import proteinclaw.core.config as config_mod
from proteinclaw.core.config import SUPPORTED_MODELS
from proteinclaw.cli.tui.screens.main import MainScreen

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

# Providers that reuse another provider's SDK in SUPPORTED_MODELS but are distinct here
_PROVIDER_MODELS_OVERRIDE: dict[str, list[str]] = {
    "minimax": ["minimax-text-01"],
}


def _models_for_provider(provider: str) -> list[str]:
    if provider in _PROVIDER_MODELS_OVERRIDE:
        return _PROVIDER_MODELS_OVERRIDE[provider]
    return [m for m, cfg in SUPPORTED_MODELS.items() if cfg["provider"] == provider]


def _display_name(provider_id: str) -> str:
    return next(display for pid, display, _ in _PROVIDERS if pid == provider_id)


class SetupScreen(Screen):
    """Codex-style progressive onboarding: completed steps stack above the active card."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #outer {
        width: 64;
        height: auto;
    }
    #title {
        text-align: center;
        text-style: bold;
        margin: 0 0 0 0;
    }
    #subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }
    #summaries {
        margin: 0 0 1 2;
        height: auto;
    }
    #card {
        border: solid $primary;
        padding: 1 2;
        height: auto;
    }
    #action-title {
        text-style: bold;
        margin: 0 0 1 0;
    }
    #helper-text {
        color: $text-muted;
        margin: 1 0 0 0;
    }
    #footer-hint {
        color: $text-muted;
        margin: 1 0 0 2;
    }
    Input {
        margin: 0 0 0 0;
    }
    Select {
        margin: 0 0 0 0;
    }
    """

    current_step: reactive[int] = reactive(1, init=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_provider: str = ""
        self._api_key: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="outer"):
            yield Label("ProteinClaw", id="title")
            yield Label("Set up your default model to get started.", id="subtitle")
            yield Vertical(id="summaries")
            with Vertical(id="card"):
                yield Label("", id="action-title")
                yield Vertical(id="card-content")
                yield Label("", id="helper-text")
            yield Label("", id="footer-hint")

    async def on_mount(self) -> None:
        await self._render_step()

    async def watch_current_step(self, step: int) -> None:  # noqa: ARG002
        await self._render_step()

    async def _render_step(self) -> None:
        step = self.current_step
        card_content = self.query_one("#card-content", Vertical)
        action_title = self.query_one("#action-title", Label)
        helper_text = self.query_one("#helper-text", Label)
        footer_hint = self.query_one("#footer-hint", Label)

        await card_content.remove_children()

        if step == 1:
            action_title.update("Choose a provider")
            helper_text.update("Provider decides which API key and models appear next.")
            footer_hint.update("")
            options = [(display, pid) for pid, display, _ in _PROVIDERS]
            select: Select[str] = Select(options, id="provider-select")
            await card_content.mount(select)
            select.focus()

        elif step == 2:
            name = _display_name(self._selected_provider)
            action_title.update(f"Enter your {name} API key")
            helper_text.update(f"Provider: {name}")
            footer_hint.update("Enter continue   Esc skip")
            inp = Input(placeholder="Paste your API key here", password=True, id="api-key-input")
            await card_content.mount(inp)
            inp.focus()

        elif step == 3:
            name = _display_name(self._selected_provider)
            action_title.update("Choose a default model")
            helper_text.update(f"Provider: {name}")
            footer_hint.update("Select a model to continue")
            models = _models_for_provider(self._selected_provider)
            options = [(m, m) for m in models]
            select = Select(options, id="model-select")
            await card_content.mount(select)
            select.focus()

    async def _append_summary(self, text: str) -> None:
        summaries = self.query_one("#summaries", Vertical)
        await summaries.mount(Label(text))

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            return

        if event.select.id == "provider-select":
            self._selected_provider = str(event.value)
            name = _display_name(self._selected_provider)
            next_step = 3 if self._selected_provider == "ollama" else 2
            await self._advance_with_summary(f"✓ Provider  {name}", next_step)

        elif event.select.id == "model-select":
            self._finish(str(event.value))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self._api_key = event.value.strip()
            summary = "✓ API key   entered" if self._api_key else "✓ API key   skipped"
            await self._advance_with_summary(summary, 3)

    async def on_key(self, event) -> None:  # type: ignore[override]
        focused = self.focused
        if event.key == "escape" and getattr(focused, "id", None) == "api-key-input":
            self._api_key = ""
            await self._advance_with_summary("✓ API key   skipped", 3)

    async def _advance_with_summary(self, summary_text: str, next_step: int) -> None:
        await self._append_summary(summary_text)
        self.current_step = next_step

    def _finish(self, model: str) -> None:
        keys: dict[str, str] = {}
        if self._api_key and self._selected_provider != "ollama":
            _, _, env_key = next(p for p in _PROVIDERS if p[0] == self._selected_provider)
            if env_key:
                keys[env_key] = self._api_key

        config_mod.save_user_config(keys, model)
        config_mod.load_user_config()

        self.app.switch_screen(MainScreen())
