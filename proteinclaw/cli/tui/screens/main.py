from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Static

from proteinclaw.core.agent.events import (
    DoneEvent, ErrorEvent, ObservationEvent,
    ThinkingEvent, TokenEvent, ToolCallEvent,
)
from proteinclaw.core.agent.loop import run
from proteinclaw.core.config import SUPPORTED_MODELS, settings
from proteinclaw.cli.tui.widgets.conversation import ConversationWidget
from proteinclaw.cli.tui.widgets.status_bar import StatusBar


class MainScreen(Screen):
    """Three-zone conversation interface: status bar + conversation + input."""

    CSS = """
    MainScreen {
        layout: vertical;
    }
    Input {
        dock: bottom;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, model: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model or settings.default_model
        self._history: list[dict] = []

    def compose(self) -> ComposeResult:
        yield StatusBar(self._model, id="status")
        yield ConversationWidget(id="conversation")
        yield Input(
            placeholder="Ask ProteinClaw... (/model /tools /clear /exit)",
            id="input",
        )

    def on_mount(self) -> None:
        """Focus the input field so keyboard events are routed to it."""
        self.query_one("#input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        self.query_one("#input", Input).value = ""
        if not query:
            return

        if query.startswith("/"):
            await self._handle_command(query)
            return

        conv = self.query_one("#conversation", ConversationWidget)
        status = self.query_one("#status", StatusBar)

        await conv.mount(Static(f"[bold blue]> {query}[/bold blue]", markup=True))
        self._history.append({"role": "user", "content": query})

        response_tokens: list[str] = []
        first_event = True

        async for ev in run(query=query, history=self._history[:-1], model=self._model):
            if first_event:
                status.set_state("thinking")
                first_event = False

            if isinstance(ev, ThinkingEvent):
                conv.append_thinking(ev.content)
            elif isinstance(ev, TokenEvent):
                conv.append_token(ev.content)
                response_tokens.append(ev.content)
            elif isinstance(ev, ToolCallEvent):
                conv.add_tool_card(ev.tool, ev.args)
            elif isinstance(ev, ObservationEvent):
                conv.complete_tool_card(ev.result)
            elif isinstance(ev, DoneEvent):
                status.set_state("ready")
            elif isinstance(ev, ErrorEvent):
                status.set_state("error", ev.message)
                response_tokens.append(f"[Error: {ev.message}]")

        if response_tokens:
            self._history.append(
                {"role": "assistant", "content": "".join(response_tokens)}
            )

    async def _handle_command(self, cmd: str) -> None:
        parts = cmd.split()
        conv = self.query_one("#conversation", ConversationWidget)
        status = self.query_one("#status", StatusBar)

        if parts[0] == "/clear":
            self._history = []
            conv.clear_conversation()

        elif parts[0] == "/exit":
            self.app.exit()

        elif parts[0] == "/model":
            if len(parts) < 2:
                available = ", ".join(SUPPORTED_MODELS)
                await conv.mount(Static(
                    f"[yellow]Usage: /model <name>. Available: {available}[/yellow]",
                    markup=True,
                ))
            elif parts[1] in SUPPORTED_MODELS:
                self._model = parts[1]
                status.set_model(self._model)
                await conv.mount(Static(
                    f"[green]Switched to model: {self._model}[/green]",
                    markup=True,
                ))
            else:
                available = ", ".join(SUPPORTED_MODELS)
                await conv.mount(Static(
                    f"[red]Unknown model '{parts[1]}'. Available: {available}[/red]",
                    markup=True,
                ))

        elif parts[0] == "/tools":
            from proteinbox.tools.registry import discover_tools
            tools = discover_tools()
            for name, tool in tools.items():
                await conv.mount(Static(
                    f"[cyan]{name}[/cyan]: {tool.description}",
                    markup=True,
                ))

        else:
            await conv.mount(Static(
                f"[yellow]Unknown command '{parts[0]}'. Try /model /tools /clear /exit[/yellow]",
                markup=True,
            ))
