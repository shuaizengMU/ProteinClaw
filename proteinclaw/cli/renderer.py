from __future__ import annotations
import sys
from proteinclaw.core.agent.events import (
    Event, ThinkingEvent, ToolCallEvent, ObservationEvent,
    TokenEvent, DoneEvent, ErrorEvent,
)


def render_event_stdout(event: Event) -> None:
    """Render an event to stdout/stderr for non-interactive (query) mode."""
    if isinstance(event, ThinkingEvent):
        print(f"[thinking] {event.content}", flush=True)
    elif isinstance(event, ToolCallEvent):
        print(f"\n[tool: {event.tool}] {event.args}", flush=True)
    elif isinstance(event, ObservationEvent):
        print(f"[result: {event.tool}] {event.result}", flush=True)
    elif isinstance(event, TokenEvent):
        print(event.content, end="", flush=True)
    elif isinstance(event, DoneEvent):
        print(flush=True)
    elif isinstance(event, ErrorEvent):
        print(f"[error] {event.message}", file=sys.stderr, flush=True)
