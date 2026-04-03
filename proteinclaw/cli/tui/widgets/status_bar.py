from __future__ import annotations
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class StatusBar(Widget):
    """Top status bar showing model name and agent state."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
        dock: top;
    }
    """

    state: reactive[str] = reactive("ready")

    def __init__(self, model: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model

    def compose(self) -> ComposeResult:
        yield Label(self._format(), id="status-label")

    def _format(self) -> str:
        return f"ProteinClaw ── model: {self._model} ── {self.state}"

    def watch_state(self, _value: str) -> None:
        if self.is_mounted:
            self.query_one("#status-label", Label).update(self._format())

    def set_state(self, state: str, message: str = "") -> None:
        """Set the agent state. 'error' auto-resets to 'ready' after 3 seconds."""
        self.state = state
        if state == "error":
            self.set_timer(3.0, lambda: self.set_state("ready"))

    def set_model(self, model: str) -> None:
        """Update the displayed model name."""
        self._model = model
        if self.is_mounted:
            self.query_one("#status-label", Label).update(self._format())
