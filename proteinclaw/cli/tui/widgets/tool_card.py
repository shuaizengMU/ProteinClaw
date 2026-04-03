from __future__ import annotations
import json
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label


class ToolCard(Widget):
    """Inline bordered card displaying a tool call and its result."""

    DEFAULT_CSS = """
    ToolCard {
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
        height: auto;
    }
    """

    def __init__(self, tool: str, args: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tool = tool
        self._args = args

    def compose(self) -> ComposeResult:
        args_str = json.dumps(self._args)
        yield Label(
            f"[bold]▶ {self._tool}[/bold]  {args_str}",
            id="tool-name",
            markup=True,
        )
        yield Label("[dim]...[/dim]", id="result", markup=True)

    def set_result(self, result: object) -> None:
        """Update the result label with the observation value."""
        self.query_one("#result", Label).update(str(result))
