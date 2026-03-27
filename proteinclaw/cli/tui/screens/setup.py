from __future__ import annotations
import os

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select

import proteinclaw.core.config as config_mod
from proteinclaw.core.config import SUPPORTED_MODELS


_KEY_FIELDS: list[tuple[str, str]] = [
    ("ANTHROPIC_API_KEY", "Anthropic API Key"),
    ("OPENAI_API_KEY", "OpenAI API Key"),
    ("DEEPSEEK_API_KEY", "DeepSeek API Key"),
    ("MINIMAX_API_KEY", "MiniMax API Key"),
]


class SetupScreen(Screen):
    """First-run API key configuration wizard."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #setup-container {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }
    Label {
        margin: 0 0 0 0;
    }
    Input {
        margin: 0 0 1 0;
    }
    Button {
        margin: 1 0 0 0;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-container"):
            yield Label("Welcome to ProteinClaw!\nLet's configure your API keys.\n")
            for env_key, display_label in _KEY_FIELDS:
                yield Label(f"{display_label}:")
                yield Input(
                    placeholder=f"{display_label} (press Enter to skip)",
                    password=True,
                    id=env_key,
                )
            yield Label("\nDefault model:")
            yield Select(
                [(m, m) for m in SUPPORTED_MODELS],
                value="deepseek-chat",
                id="default-model",
            )
            yield Button("Save & Continue", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        """Pre-fill any API key fields that are already in the environment."""
        for env_key, _ in _KEY_FIELDS:
            value = os.environ.get(env_key, "")
            if value:
                self.query_one(f"#{env_key}", Input).value = value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save-btn":
            return

        keys: dict[str, str] = {}
        for env_key, _ in _KEY_FIELDS:
            value = self.query_one(f"#{env_key}", Input).value.strip()
            if value:
                keys[env_key] = value

        model_select = self.query_one("#default-model", Select)
        default_model = str(model_select.value) if model_select.value != Select.BLANK else "deepseek-chat"

        config_mod.save_user_config(keys, default_model)

        # Reload config (reads the just-saved file and reinitialises settings singleton)
        config_mod.load_user_config()

        # Import here to avoid circular import at module level
        from proteinclaw.cli.tui.screens.main import MainScreen  # noqa: PLC0415
        self.app.switch_screen(MainScreen())
