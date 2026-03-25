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
    type: str = "thinking"
    content: str = ""


@dataclass
class ToolCallEvent(Event):
    type: str = "tool_call"
    tool: str = ""
    args: dict = field(default_factory=dict)


@dataclass
class ObservationEvent(Event):
    type: str = "observation"
    tool: str = ""
    result: Any = None


@dataclass
class TokenEvent(Event):
    type: str = "token"
    content: str = ""


@dataclass
class DoneEvent(Event):
    type: str = "done"


@dataclass
class ErrorEvent(Event):
    type: str = "error"
    message: str = ""
