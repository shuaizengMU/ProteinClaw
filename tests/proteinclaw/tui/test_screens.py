from __future__ import annotations
import os
from unittest.mock import patch

import proteinclaw.core.config as config_mod
from proteinclaw.cli.tui.screens.setup import SetupScreen
from textual.app import App, ComposeResult
from textual.widgets import Input


class _SetupApp(App):
    """Minimal host that starts on SetupScreen."""

    def on_mount(self) -> None:
        self.push_screen(SetupScreen())

    def query(self, selector=None):  # type: ignore[override]
        """Delegate queries to the active screen so tests work with push_screen."""
        if selector is None:
            return self.screen.query()
        return self.screen.query(selector)

    def query_one(self, selector, expect_type=None):  # type: ignore[override]
        """Delegate query_one to the active screen."""
        if expect_type is not None:
            return self.screen.query_one(selector, expect_type)
        return self.screen.query_one(selector)


async def test_setup_screen_shows_key_inputs():
    async with _SetupApp().run_test() as pilot:
        inputs = pilot.app.query(Input)
        input_ids = {inp.id for inp in inputs}
        assert "ANTHROPIC_API_KEY" in input_ids
        assert "DEEPSEEK_API_KEY" in input_ids


async def test_setup_screen_prefills_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-prefill")
    async with _SetupApp().run_test() as pilot:
        field = pilot.app.query_one("#ANTHROPIC_API_KEY", Input)
        assert field.value == "sk-ant-prefill"


async def test_setup_screen_save_calls_save_user_config():
    saved: list[tuple] = []

    def _fake_save(keys, model):
        saved.append((keys, model))

    with patch.object(config_mod, "save_user_config", _fake_save), \
         patch.object(config_mod, "Settings", config_mod.Settings):
        async with _SetupApp().run_test(size=(120, 50)) as pilot:
            pilot.app.query_one("#DEEPSEEK_API_KEY", Input).value = "ds-test"
            await pilot.click("#save-btn")
            await pilot.pause()

    assert len(saved) == 1
    assert saved[0][0].get("DEEPSEEK_API_KEY") == "ds-test"


from unittest.mock import patch
from proteinclaw.cli.tui.screens.main import MainScreen
from proteinclaw.core.agent.events import TokenEvent, DoneEvent, ErrorEvent, ToolCallEvent, ObservationEvent
from proteinclaw.cli.tui.widgets.status_bar import StatusBar
from proteinclaw.cli.tui.widgets.conversation import ConversationWidget


class _MainApp(App):
    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def query_one(self, selector, expect_type=None):
        if expect_type is not None:
            return self.screen.query_one(selector, expect_type)
        return self.screen.query_one(selector)


async def test_main_screen_layout_has_required_widgets():
    async with _MainApp().run_test() as pilot:
        pilot.app.query_one(StatusBar)
        pilot.app.query_one(ConversationWidget)
        from textual.widgets import Input
        pilot.app.query_one(Input)


async def test_main_screen_clear_command():
    async with _MainApp().run_test() as pilot:
        from textual.widgets import Input
        inp = pilot.app.query_one(Input)
        inp.value = "/clear"
        await pilot.press("enter")
        await pilot.pause()
        conv = pilot.app.query_one(ConversationWidget)
        assert len(conv.children) == 0


async def test_main_screen_unknown_command_shows_message():
    async with _MainApp().run_test() as pilot:
        from textual.widgets import Input
        inp = pilot.app.query_one(Input)
        inp.value = "/notacommand"
        await pilot.press("enter")
        await pilot.pause()
        conv = pilot.app.query_one(ConversationWidget)
        assert len(conv.children) > 0


async def test_main_screen_model_command_switches_model():
    async with _MainApp().run_test() as pilot:
        from textual.widgets import Input
        inp = pilot.app.query_one(Input)
        inp.value = "/model deepseek-chat"
        await pilot.press("enter")
        await pilot.pause()
        bar = pilot.app.query_one(StatusBar)
        assert "deepseek-chat" in str(bar.query_one("#status-label").content)


async def test_main_screen_streams_token_events():
    async def _fake_run(query, history, model):
        yield TokenEvent(content="Hello")
        yield TokenEvent(content=" world")
        yield DoneEvent()

    with patch("proteinclaw.cli.tui.screens.main.run", side_effect=_fake_run):
        async with _MainApp().run_test() as pilot:
            from textual.widgets import Input
            inp = pilot.app.query_one(Input)
            inp.value = "What is P04637?"
            await pilot.press("enter")
            await pilot.pause(delay=0.1)
            conv = pilot.app.query_one(ConversationWidget)
            assert len(conv.children) >= 1
