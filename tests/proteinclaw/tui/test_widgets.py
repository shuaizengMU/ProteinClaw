from __future__ import annotations
from textual.app import App, ComposeResult

from proteinclaw.cli.tui.widgets.tool_card import ToolCard


# Minimal host app for widget testing
class _ToolCardApp(App):
    def compose(self) -> ComposeResult:
        yield ToolCard("uniprot", {"id": "P04637"})


async def test_tool_card_shows_tool_name():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        # The tool name label has id="tool-name"
        label_text = str(card.query_one("#tool-name").content)
        assert "uniprot" in label_text


async def test_tool_card_shows_args():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        label_text = str(card.query_one("#tool-name").content)
        assert "P04637" in label_text


async def test_tool_card_result_initially_pending():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        result_text = str(card.query_one("#result").content)
        assert "..." in result_text


async def test_tool_card_set_result_updates_label():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        card.set_result("TP53_HUMAN, 393 aa")
        await pilot.pause()
        result_text = str(card.query_one("#result").content)
        assert "TP53_HUMAN" in result_text


from proteinclaw.cli.tui.widgets.status_bar import StatusBar


class _StatusBarApp(App):
    def compose(self) -> ComposeResult:
        yield StatusBar("deepseek-chat")


async def test_status_bar_shows_model():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        label_text = str(bar.query_one("#status-label").content)
        assert "deepseek-chat" in label_text


async def test_status_bar_initial_state_ready():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        label_text = str(bar.query_one("#status-label").content)
        assert "ready" in label_text


async def test_status_bar_set_state_thinking():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        bar.set_state("thinking")
        await pilot.pause()
        label_text = str(bar.query_one("#status-label").content)
        assert "thinking" in label_text


async def test_status_bar_set_model():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        bar.set_model("gpt-4o")
        await pilot.pause()
        label_text = str(bar.query_one("#status-label").content)
        assert "gpt-4o" in label_text
