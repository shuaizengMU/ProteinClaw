from dataclasses import asdict
from proteinclaw.core.agent.events import (
    ThinkingEvent, ToolCallEvent, ObservationEvent,
    TokenEvent, DoneEvent, ErrorEvent,
)


def test_thinking_event_to_dict():
    e = ThinkingEvent(content="planning")
    d = e.to_dict()
    assert d == {"type": "thinking", "content": "planning"}


def test_tool_call_event_defaults():
    e = ToolCallEvent(tool="uniprot")
    assert e.args == {}
    d = e.to_dict()
    assert d["type"] == "tool_call"
    assert d["tool"] == "uniprot"
    assert d["args"] == {}


def test_tool_call_event_with_args():
    e = ToolCallEvent(tool="uniprot", args={"id": "P04637"})
    assert e.to_dict()["args"] == {"id": "P04637"}


def test_observation_event_to_dict():
    e = ObservationEvent(tool="uniprot", result={"name": "TP53"})
    d = e.to_dict()
    assert d["type"] == "observation"
    assert d["result"] == {"name": "TP53"}


def test_token_event_to_dict():
    e = TokenEvent(content="hello ")
    assert e.to_dict() == {"type": "token", "content": "hello "}


def test_done_event_to_dict():
    e = DoneEvent()
    assert e.to_dict() == {"type": "done"}


def test_error_event_to_dict():
    e = ErrorEvent(message="oops")
    assert e.to_dict() == {"type": "error", "message": "oops"}
