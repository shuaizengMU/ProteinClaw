from __future__ import annotations
import pytest
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
