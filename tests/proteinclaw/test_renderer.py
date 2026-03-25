import sys
from io import StringIO
from proteinclaw.cli.renderer import render_event_stdout
from proteinclaw.core.agent.events import (
    ThinkingEvent, ToolCallEvent, ObservationEvent,
    TokenEvent, DoneEvent, ErrorEvent
)


def capture(event):
    """Run render_event_stdout and return (stdout, stderr) strings."""
    out, err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    render_event_stdout(event)
    sys.stdout, sys.stderr = old_out, old_err
    return out.getvalue(), err.getvalue()


def test_renders_thinking():
    out, _ = capture(ThinkingEvent(content="planning"))
    assert "planning" in out


def test_renders_tool_call():
    out, _ = capture(ToolCallEvent(tool="uniprot", args={"id": "P04637"}))
    assert "uniprot" in out


def test_renders_token_without_newline():
    out, _ = capture(TokenEvent(content="hello "))
    assert out == "hello "  # no trailing newline — tokens are streamed inline


def test_renders_done_adds_newline():
    out, _ = capture(DoneEvent())
    assert out == "\n"


def test_renders_error_to_stderr():
    _, err = capture(ErrorEvent(message="something broke"))
    assert "something broke" in err
