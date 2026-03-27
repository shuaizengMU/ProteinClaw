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


from proteinclaw.cli.tui.widgets.conversation import ConversationWidget


class _ConvApp(App):
    def compose(self) -> ComposeResult:
        yield ConversationWidget(id="conv")


async def test_conversation_append_thinking_mounts_widget():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        assert len(conv.children) == 0
        conv.append_thinking("planning next step")
        await pilot.pause()
        assert len(conv.children) == 1


async def test_conversation_append_token_accumulates():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.append_token("Hello")
        conv.append_token(", world")
        await pilot.pause()
        # Only one Static widget for the whole streamed response
        assert len(conv.children) == 1


async def test_conversation_add_tool_card_sets_pending():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.add_tool_card("uniprot", {"id": "P04637"})
        await pilot.pause()
        assert conv._pending_card is not None
        assert isinstance(conv._pending_card, ToolCard)


async def test_conversation_complete_tool_card_clears_pending():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.add_tool_card("uniprot", {"id": "P04637"})
        await pilot.pause()
        conv.complete_tool_card("TP53_HUMAN")
        assert conv._pending_card is None


async def test_conversation_tool_card_new_response_resets_buffer():
    """append_token after add_tool_card creates a new Static, not appending to old buffer."""
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.append_token("before tool")
        await pilot.pause()
        conv.add_tool_card("blast", {"sequence": "MKTII"})
        await pilot.pause()
        conv.append_token("after tool")
        await pilot.pause()
        # Should have: 1 Static (before), 1 ToolCard, 1 Static (after) = 3 children
        assert len(conv.children) == 3


async def test_conversation_clear_removes_all_children():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.append_token("hello")
        conv.add_tool_card("uniprot", {"id": "P04637"})
        await pilot.pause()
        conv.clear_conversation()
        await pilot.pause()
        assert len(conv.children) == 0
        assert conv._pending_card is None
