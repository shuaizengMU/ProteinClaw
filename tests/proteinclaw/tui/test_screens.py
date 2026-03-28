from __future__ import annotations

from unittest.mock import patch

import pytest
import proteinclaw.core.config as config_mod
from proteinclaw.cli.tui.screens.setup import SetupScreen
from textual.app import App
from textual.containers import Vertical
from textual.widgets import Input, Label, Select


class _SetupApp(App):
    """Minimal host that starts on SetupScreen."""

    async def on_mount(self) -> None:
        await self.push_screen(SetupScreen())


@pytest.mark.asyncio
async def test_setup_flow_initial_state_shows_provider_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        select = pilot.app.screen.query_one("#provider-select", Select)
        assert select is not None


@pytest.mark.asyncio
async def test_setup_flow_provider_selection_advances_to_api_key_input():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        inp = pilot.app.screen.query_one("#api-key-input", Input)
        assert inp is not None


@pytest.mark.asyncio
async def test_setup_flow_api_key_label_contains_provider_display_name():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "deepseek"
        await pilot.pause()
        label_text = str(pilot.app.screen.query_one("#action-title", Label).content)
        assert "DeepSeek" in label_text


@pytest.mark.asyncio
async def test_setup_flow_ollama_skips_api_key_and_goes_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "ollama"
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


@pytest.mark.asyncio
async def test_setup_flow_enter_on_api_key_advances_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        pilot.app.screen.query_one("#api-key-input", Input).value = "sk-ant-test"
        await pilot.press("enter")
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


@pytest.mark.asyncio
async def test_setup_flow_escape_on_api_key_skips_and_advances_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


@pytest.mark.asyncio
async def test_setup_flow_complete_saves_correct_key_and_model():
    saved: list[tuple] = []

    def _fake_save(keys, model):
        saved.append((keys, model))

    with (
        patch.object(config_mod, "save_user_config", _fake_save),
        patch.object(config_mod, "load_user_config", lambda: None),
        patch("proteinclaw.cli.tui.screens.setup.MainScreen"),
        patch("textual.app.App.switch_screen"),
    ):
        async with _SetupApp().run_test(size=(120, 50)) as pilot:
            pilot.app.screen.query_one("#provider-select", Select).value = "deepseek"
            await pilot.pause()
            pilot.app.screen.query_one("#api-key-input", Input).value = "ds-key"
            await pilot.press("enter")
            await pilot.pause()
            pilot.app.screen.query_one("#model-select", Select).value = "deepseek-chat"
            await pilot.pause()

    assert len(saved) == 1
    assert saved[0][0] == {"DEEPSEEK_API_KEY": "ds-key"}
    assert saved[0][1] == "deepseek-chat"


@pytest.mark.asyncio
async def test_setup_flow_provider_summary_visible_after_selection():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        labels = pilot.app.screen.query_one("#summaries", Vertical).query(Label)
        texts = [str(lbl.content) for lbl in labels]
        assert any("Anthropic" in t for t in texts)


@pytest.mark.asyncio
async def test_setup_flow_api_key_summary_visible_after_submission():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        pilot.app.screen.query_one("#api-key-input", Input).value = "sk-test"
        await pilot.press("enter")
        await pilot.pause()
        labels = pilot.app.screen.query_one("#summaries", Vertical).query(Label)
        texts = [str(lbl.content) for lbl in labels]
        assert any("API key" in t and "entered" in t for t in texts)


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
