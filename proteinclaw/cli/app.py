from __future__ import annotations
import argparse
import asyncio
import sys

from proteinclaw.core.config import settings, SUPPORTED_MODELS
from proteinclaw.core.agent.loop import run
from proteinclaw.core.agent.events import TokenEvent, ErrorEvent, ToolCallEvent, ObservationEvent
from proteinclaw.cli.renderer import render_event_stdout


# ── Non-interactive query mode ─────────────────────────────────────────────

async def _run_query(text: str, model: str | None) -> int:
    """Run a single query and stream output to stdout. Returns exit code."""
    resolved_model = model if model in SUPPORTED_MODELS else settings.default_model
    exit_code = 0
    async for event in run(query=text, history=[], model=resolved_model):
        render_event_stdout(event)
        if isinstance(event, ErrorEvent):
            exit_code = 1
    return exit_code


# ── Interactive TUI ────────────────────────────────────────────────────────

def _run_tui() -> None:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Input, RichLog
    from textual.binding import Binding

    class ProteinClawApp(App):
        TITLE = "ProteinClaw"
        BINDINGS = [Binding("ctrl+c", "quit", "Quit")]
        CSS = """
        RichLog { height: 1fr; border: solid $primary; padding: 0 1; }
        Input { dock: bottom; margin: 0 0 1 0; }
        """

        def __init__(self) -> None:
            super().__init__()
            self.model = settings.default_model
            self.history: list[dict] = []

        def compose(self) -> ComposeResult:
            yield Header()
            yield RichLog(id="log", wrap=True, highlight=True, markup=True)
            yield Input(placeholder=f"Ask ProteinClaw... (model: {self.model})", id="input")
            yield Footer()

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            query = event.value.strip()
            self.query_one("#input", Input).value = ""
            if not query:
                return

            log = self.query_one("#log", RichLog)

            if query.startswith("/"):
                await self._handle_command(query, log)
                return

            log.write(f"[bold blue]> {query}[/bold blue]")
            self.history.append({"role": "user", "content": query})
            response_tokens: list[str] = []

            async for ev in run(
                query=query,
                history=self.history[:-1],
                model=self.model,
            ):
                if isinstance(ev, TokenEvent):
                    response_tokens.append(ev.content)
                    log.write(ev.content, end="")
                elif isinstance(ev, ToolCallEvent):
                    log.write(f"\n[bold yellow]▶ [tool: {ev.tool}][/bold yellow] {ev.args}")
                elif isinstance(ev, ObservationEvent):
                    log.write(f"  [dim]└ {ev.result}[/dim]")
                elif isinstance(ev, ErrorEvent):
                    log.write(f"[bold red][error] {ev.message}[/bold red]")
                    response_tokens.append(f"[Error: {ev.message}]")

            log.write("")  # newline after streaming ends
            self.history.append({"role": "assistant", "content": "".join(response_tokens)})

        async def _handle_command(self, cmd: str, log: RichLog) -> None:
            parts = cmd.split()
            if parts[0] == "/clear":
                self.history = []
                log.clear()
            elif parts[0] == "/exit":
                self.exit()
            elif parts[0] == "/model":
                if len(parts) < 2:
                    log.write(f"[yellow]Usage: /model <name>. Available: {', '.join(SUPPORTED_MODELS)}[/yellow]")
                elif parts[1] in SUPPORTED_MODELS:
                    self.model = parts[1]
                    self.query_one("#input", Input).placeholder = f"Ask ProteinClaw... (model: {self.model})"
                    log.write(f"[green]Switched to model: {self.model}[/green]")
                else:
                    log.write(f"[red]Unknown model '{parts[1]}'. Available: {', '.join(SUPPORTED_MODELS)}[/red]")
            elif parts[0] == "/tools":
                from proteinbox.tools.registry import discover_tools
                tools = discover_tools()
                for name, tool in tools.items():
                    log.write(f"[cyan]{name}[/cyan]: {tool.description}")
            else:
                log.write(f"[yellow]Unknown command '{parts[0]}'. Try /model, /tools, /clear, /exit[/yellow]")

    ProteinClawApp().run()


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="proteinclaw",
        description="ProteinClaw — AI agent for protein bioinformatics",
    )
    subparsers = parser.add_subparsers(dest="command")

    query_parser = subparsers.add_parser("query", help="Run a single query and exit")
    query_parser.add_argument("text", help="The query to run")
    query_parser.add_argument("--model", default=None, help="LLM model to use")

    args = parser.parse_args()

    if args.command == "query":
        exit_code = asyncio.run(_run_query(args.text, args.model))
        sys.exit(exit_code)
    else:
        _run_tui()
