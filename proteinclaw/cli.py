"""ProteinClaw command-line interface.

Commands
--------
proteinclaw server          Start the backend API server (default port 8765).
proteinclaw query "<text>"  One-shot agent query; prints streamed output to stdout.
"""
from __future__ import annotations

import argparse
import asyncio
import sys


# ── server ────────────────────────────────────────────────────────────────────

def _cmd_server(args: argparse.Namespace) -> None:
    import uvicorn
    from proteinclaw.core.config import load_user_config
    load_user_config()
    uvicorn.run(
        "proteinclaw.server.main:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


# ── query ─────────────────────────────────────────────────────────────────────

async def _run_query(query: str, model: str) -> None:
    from proteinclaw.core.config import load_user_config, settings
    from proteinclaw.core.agent.loop import run
    from proteinclaw.core.agent.events import (
        ToolCallEvent, ObservationEvent, TokenEvent, DoneEvent, ErrorEvent,
    )

    load_user_config()
    resolved_model = model or settings.default_model

    try:
        from rich.console import Console
        from rich.text import Text
        console = Console()
        _rich = True
    except ImportError:
        _rich = False

    async for event in run(query=query, history=[], model=resolved_model):
        if isinstance(event, ToolCallEvent):
            line = f"  [tool: {event.tool}] {event.args}"
            if _rich:
                console.print(Text(line, style="dim cyan"))
            else:
                print(line)
        elif isinstance(event, TokenEvent):
            print(event.content, end="", flush=True)
        elif isinstance(event, DoneEvent):
            print()
        elif isinstance(event, ErrorEvent):
            msg = f"\nError: {event.message}"
            if _rich:
                console.print(Text(msg, style="bold red"))
            else:
                print(msg, file=sys.stderr)
            sys.exit(1)


def _cmd_query(args: argparse.Namespace) -> None:
    query = " ".join(args.query)
    asyncio.run(_run_query(query, model=args.model))


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="proteinclaw",
        description="ProteinClaw — AI agent for protein bioinformatics",
    )
    sub = parser.add_subparsers(dest="command")

    # server
    p_server = sub.add_parser("server", help="Start the backend API server")
    p_server.add_argument("--host", default="127.0.0.1")
    p_server.add_argument("--port", type=int, default=8765)
    p_server.set_defaults(func=_cmd_server)

    # query
    p_query = sub.add_parser("query", help="Run a one-shot agent query")
    p_query.add_argument("query", nargs="+", help="Question to answer")
    p_query.add_argument("--model", default="", help="LLM model (default: from config)")
    p_query.set_defaults(func=_cmd_query)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)
