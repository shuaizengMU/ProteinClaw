from __future__ import annotations
from textual.containers import VerticalScroll
from textual.widgets import Static

from proteinclaw.cli.tui.widgets.tool_card import ToolCard


class ConversationWidget(VerticalScroll):
    """Scrollable conversation area with mixed Static text and ToolCard children."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._pending_card: ToolCard | None = None
        self._current_response: Static | None = None
        self._response_buffer: list[str] = []

    def append_thinking(self, content: str) -> None:
        """Mount a dim italic Static for a ThinkingEvent. Not added to history."""
        self._current_response = None
        self._response_buffer = []
        self.mount(Static(f"[dim italic]{content}[/dim italic]", markup=True))
        self.scroll_end(animate=False)

    def append_token(self, content: str) -> None:
        """Append a token to the current response Static, creating it if needed."""
        if self._current_response is None:
            self._current_response = Static("", markup=False)
            self.mount(self._current_response)
            self._response_buffer = []
        self._response_buffer.append(content)
        self._current_response.update("".join(self._response_buffer))
        self.scroll_end(animate=False)

    def add_tool_card(self, tool: str, args: dict) -> None:
        """Mount a new ToolCard and set it as the pending card for the next result."""
        self._current_response = None
        self._response_buffer = []
        card = ToolCard(tool, args)
        self.mount(card)
        self._pending_card = card
        self.scroll_end(animate=False)

    def complete_tool_card(self, result: object) -> None:
        """Route an ObservationEvent result to the pending ToolCard, then clear it."""
        if self._pending_card is not None:
            self._pending_card.set_result(result)
            self._pending_card = None

    def clear_conversation(self) -> None:
        """Remove all children and reset internal state."""
        self.remove_children()
        self._pending_card = None
        self._current_response = None
        self._response_buffer = []
