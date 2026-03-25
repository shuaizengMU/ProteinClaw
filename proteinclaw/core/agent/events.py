from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class Event:
    type: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ThinkingEvent(Event):
    type: str = field(default="thinking", init=False)
    content: str = ""


@dataclass
class ToolCallEvent(Event):
    type: str = field(default="tool_call", init=False)
    tool: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ObservationEvent(Event):
    type: str = field(default="observation", init=False)
    tool: str = ""
    result: Any = None


@dataclass
class TokenEvent(Event):
    type: str = field(default="token", init=False)
    content: str = ""


@dataclass
class DoneEvent(Event):
    type: str = field(default="done", init=False)


@dataclass
class ErrorEvent(Event):
    type: str = field(default="error", init=False)
    message: str = ""
