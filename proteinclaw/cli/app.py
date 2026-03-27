from __future__ import annotations
import argparse
import asyncio
import sys

from proteinclaw.core.config import settings, SUPPORTED_MODELS
from proteinclaw.core.agent.loop import run
from proteinclaw.core.agent.events import ErrorEvent
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
    from proteinclaw.cli.tui.app import ProteinClawApp
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
