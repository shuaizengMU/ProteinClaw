from __future__ import annotations

from textual.app import App

from proteinclaw.core.config import load_user_config, needs_setup


class ProteinClawApp(App):
    """Top-level Textual application for ProteinClaw."""

    TITLE = "ProteinClaw"

    async def on_mount(self) -> None:
        load_user_config()
        if needs_setup():
            from proteinclaw.cli.tui.screens.setup import SetupScreen
            self.switch_screen(SetupScreen())
        else:
            from proteinclaw.cli.tui.screens.main import MainScreen
            self.switch_screen(MainScreen())
