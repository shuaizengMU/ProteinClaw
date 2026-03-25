# ProteinClaw Architecture Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate ProteinClaw from a Docker-based web app to a local-first architecture with a three-layer core/server/cli separation, a Textual interactive CLI, and a Tauri desktop app.

**Architecture:** Pure Python core layer (no web/CLI deps) exposes an async generator of typed Event objects consumed by the FastAPI server (WebSocket) and a new Textual TUI. Tauri (Rust) wraps the Python server as a desktop app using a bundled uv binary for zero-dependency install.

**Tech Stack:** Python 3.11+, FastAPI, LiteLLM, Pydantic v2, Textual, pytest / pytest-asyncio, Rust + Tauri v2, React + TypeScript

---

## File Map

```
NEW:
  proteinclaw/core/__init__.py
  proteinclaw/core/agent/__init__.py
  proteinclaw/core/agent/events.py        ← Event base class + 6 event dataclasses
  proteinclaw/core/agent/loop.py          ← migrated from proteinclaw/agent/loop.py
  proteinclaw/core/agent/llm.py           ← migrated from proteinclaw/agent/llm.py
  proteinclaw/core/agent/prompt.py        ← migrated from proteinclaw/agent/prompt.py
  proteinclaw/core/config.py              ← migrated from proteinclaw/config.py
  proteinclaw/server/__init__.py
  proteinclaw/server/main.py              ← migrated from proteinclaw/main.py
  proteinclaw/server/chat.py              ← migrated from proteinclaw/api/chat.py
  proteinclaw/server/tools.py             ← migrated from proteinclaw/api/tools.py
  proteinclaw/cli/__init__.py
  proteinclaw/cli/renderer.py             ← Event → stdout and Textual rendering
  proteinclaw/cli/app.py                  ← Textual TUI + argparse entry point
  src-tauri/tauri.conf.json
  src-tauri/Cargo.toml
  src-tauri/src/main.rs                   ← Rust: uv sidecar, server lifecycle, WebView
  src-tauri/binaries/uv-*                 ← platform-specific uv binaries
  tests/proteinclaw/test_events.py        ← new tests for events.py

MODIFIED:
  pyproject.toml                          ← add cli optional dep, scripts entry point
  tests/proteinclaw/test_config.py        ← import path update
  tests/proteinclaw/test_llm.py           ← import + patch string update
  tests/proteinclaw/test_prompt.py        ← import path update
  tests/proteinclaw/test_loop.py          ← import, patch strings, assertions on Event objects
  tests/proteinclaw/test_api.py           ← import, patch strings, mocks yield Events
  frontend/src/hooks/useChat.ts           ← read window.__BACKEND_PORT__ ?? 8000

DELETED:
  proteinclaw/agent/                      ← replaced by proteinclaw/core/agent/
  proteinclaw/api/                        ← replaced by proteinclaw/server/
  proteinclaw/main.py                     ← moved to proteinclaw/server/main.py
  proteinclaw/config.py                   ← moved to proteinclaw/core/config.py
  docker-compose.yml
```

---

## Task 1: Core Package Structure + Event Types

**Files:**
- Create: `proteinclaw/core/__init__.py`
- Create: `proteinclaw/core/agent/__init__.py`
- Create: `proteinclaw/core/agent/events.py`
- Create: `tests/proteinclaw/test_events.py`

- [ ] **Step 1: Create empty `__init__.py` files**

```bash
touch proteinclaw/core/__init__.py
touch proteinclaw/core/agent/__init__.py
```

- [ ] **Step 2: Write the failing tests for events**

Create `tests/proteinclaw/test_events.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/test_events.py -v
```

Expected: `ModuleNotFoundError: No module named 'proteinclaw.core'`

- [ ] **Step 4: Create `proteinclaw/core/agent/events.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/proteinclaw/test_events.py -v
```

Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add proteinclaw/core/ tests/proteinclaw/test_events.py
git commit -m "feat: add core package skeleton and Event type dataclasses"
```

---

## Task 2: Migrate Config to Core

**Files:**
- Create: `proteinclaw/core/config.py` (content from `proteinclaw/config.py`)
- Modify: `tests/proteinclaw/test_config.py`

- [ ] **Step 1: Update the test import to the new path**

In `tests/proteinclaw/test_config.py` line 3, change:

```python
# Before
from proteinclaw.config import Settings, SUPPORTED_MODELS
```

```python
# After
from proteinclaw.core.config import Settings, SUPPORTED_MODELS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'proteinclaw.core.config'`

- [ ] **Step 3: Create `proteinclaw/core/config.py`**

Copy `proteinclaw/config.py` exactly as-is (no content changes):

```python
from pydantic_settings import BaseSettings
from pydantic import Field


SUPPORTED_MODELS: dict[str, dict] = {
    "gpt-4o":            {"provider": "openai"},
    "claude-opus-4-5":   {"provider": "anthropic"},
    "deepseek-chat":     {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner": {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "minimax-text-01":   {"provider": "minimax",   "api_base": "https://api.minimax.chat/v1"},
    "ollama/llama3":     {"provider": "ollama",    "api_base": "http://localhost:11434"},
}


class Settings(BaseSettings):
    default_model: str = Field(default="gpt-4o", alias="DEFAULT_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    ncbi_api_key: str = Field(default="", alias="NCBI_API_KEY")

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/proteinclaw/test_config.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/core/config.py tests/proteinclaw/test_config.py
git commit -m "feat: migrate config to proteinclaw/core/config.py"
```

---

## Task 3: Migrate llm.py and prompt.py to Core

**Files:**
- Create: `proteinclaw/core/agent/llm.py`
- Create: `proteinclaw/core/agent/prompt.py`
- Modify: `tests/proteinclaw/test_llm.py`
- Modify: `tests/proteinclaw/test_prompt.py`

- [ ] **Step 1: Update test imports and patch strings**

In `tests/proteinclaw/test_llm.py`:

```python
# Line 3 — change import
from proteinclaw.core.agent.llm import call_llm, call_llm_stream, build_tools_schema

# Line 34 — change patch string
with patch("proteinclaw.core.agent.llm.litellm.completion", return_value=mock_response):

# Line 54 — change patch string
with patch("proteinclaw.core.agent.llm.litellm.completion", return_value=mock_response):
```

In `tests/proteinclaw/test_prompt.py`:

```python
# Line 2 — change import
from proteinclaw.core.agent.prompt import build_system_prompt
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/test_llm.py tests/proteinclaw/test_prompt.py -v
```

Expected: `ModuleNotFoundError: No module named 'proteinclaw.core.agent.llm'`

- [ ] **Step 3: Create `proteinclaw/core/agent/llm.py`**

Copy `proteinclaw/agent/llm.py`, updating the one import on line 5:

```python
from __future__ import annotations
import json
from typing import Any, Generator
import litellm
from proteinclaw.core.config import SUPPORTED_MODELS  # ← updated import


def build_tools_schema(tools: dict) -> list[dict]:
    """Convert TOOL_REGISTRY entries to OpenAI function-calling schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools.values()
    ]


def _get_litellm_kwargs(model: str) -> dict[str, Any]:
    cfg = SUPPORTED_MODELS.get(model, {})
    kwargs: dict[str, Any] = {"model": model}
    if "api_base" in cfg:
        kwargs["api_base"] = cfg["api_base"]
    return kwargs


def call_llm(model: str, messages: list[dict], tools: list[dict]):
    """Single (non-streaming) LLM call. Returns the response message object."""
    kwargs = _get_litellm_kwargs(model)
    response = litellm.completion(
        messages=messages,
        tools=tools or None,
        tool_choice="auto" if tools else None,
        **kwargs,
    )
    return response.choices[0].message


def call_llm_stream(model: str, messages: list[dict]) -> Generator[str, None, None]:
    """Streaming LLM call (no tools). Yields text tokens."""
    kwargs = _get_litellm_kwargs(model)
    response = litellm.completion(messages=messages, stream=True, **kwargs)
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
```

- [ ] **Step 4: Create `proteinclaw/core/agent/prompt.py`**

Copy `proteinclaw/agent/prompt.py` exactly — no changes needed (it only imports from `proteinbox`, which is not moving):

```python
from proteinbox.tools.registry import ProteinTool

SYSTEM_TEMPLATE = """\
You are ProteinClaw, an expert AI assistant for protein bioinformatics research.

You have access to the following tools:
{tool_descriptions}

When answering questions:
1. Identify which tools are needed to answer the question.
2. Call tools in a logical order, using previous results to inform next steps.
3. Synthesize all tool results into a clear, concise answer for the researcher.
4. If a tool fails, explain what went wrong and suggest alternatives.

Always cite the data source (e.g., UniProt, NCBI BLAST) when reporting results.
"""


def build_system_prompt(tools: dict[str, ProteinTool]) -> str:
    tool_descriptions = "\n".join(
        f"- **{tool.name}**: {tool.description}" for tool in tools.values()
    )
    return SYSTEM_TEMPLATE.format(tool_descriptions=tool_descriptions)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/proteinclaw/test_llm.py tests/proteinclaw/test_prompt.py -v
```

Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add proteinclaw/core/agent/llm.py proteinclaw/core/agent/prompt.py \
        tests/proteinclaw/test_llm.py tests/proteinclaw/test_prompt.py
git commit -m "feat: migrate llm.py and prompt.py to proteinclaw/core/agent/"
```

---

## Task 4: Migrate and Refactor loop.py — Async Generator of Events

**Files:**
- Create: `proteinclaw/core/agent/loop.py`
- Modify: `tests/proteinclaw/test_loop.py`

This is the most significant migration: `run_agent` becomes `run`, yields `Event` objects instead of dicts, and its parameter order changes (`query, history, model, max_steps`).

- [ ] **Step 1: Rewrite `tests/proteinclaw/test_loop.py`**

Replace the entire file:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from proteinclaw.core.agent.loop import run
from proteinclaw.core.agent.events import (
    ToolCallEvent, ObservationEvent, TokenEvent, DoneEvent, ErrorEvent
)
from proteinbox.tools.registry import ProteinTool, ToolResult, TOOL_REGISTRY


class FakeUniProtTool(ProteinTool):
    name: str = "uniprot"
    description: str = "Fake UniProt"
    parameters: dict = {
        "type": "object",
        "properties": {"accession_id": {"type": "string"}},
        "required": ["accession_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            data={"name": "TP53", "organism": "Homo sapiens"},
            display="TP53 — Homo sapiens",
        )


@pytest.fixture(autouse=True)
def patch_registry():
    with patch.dict(TOOL_REGISTRY, {"uniprot": FakeUniProtTool()}, clear=True):
        yield


def _make_tool_call_msg(tool_name: str, args: dict):
    tc = MagicMock()
    tc.id = "call_123"
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)
    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    return msg


def _make_final_msg(content: str):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    return msg


@pytest.mark.asyncio
async def test_agent_calls_tool_then_answers():
    events = []

    call_sequence = [
        _make_tool_call_msg("uniprot", {"accession_id": "P04637"}),
        _make_final_msg("P04637 is TP53 from Homo sapiens."),
    ]
    call_iter = iter(call_sequence)

    with patch("proteinclaw.core.agent.loop.call_llm", side_effect=lambda **kw: next(call_iter)):
        async for event in run(
            query="What is P04637?",
            history=[],
            model="gpt-4o",
        ):
            events.append(event)

    types = [e.type for e in events]
    assert "tool_call" in types
    assert "observation" in types
    assert "token" in types
    final_tokens = "".join(e.content for e in events if isinstance(e, TokenEvent))
    assert "TP53" in final_tokens


@pytest.mark.asyncio
async def test_agent_respects_max_steps():
    def always_tool(**kw):
        return _make_tool_call_msg("uniprot", {"accession_id": "P04637"})

    events = []
    with patch("proteinclaw.core.agent.loop.call_llm", side_effect=always_tool):
        async for event in run(
            query="loop forever",
            history=[],
            model="gpt-4o",
            max_steps=3,
        ):
            events.append(event)

    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(error_events) == 1
    assert "max" in error_events[0].message.lower() or "step" in error_events[0].message.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/test_loop.py -v
```

Expected: `ModuleNotFoundError: No module named 'proteinclaw.core.agent.loop'`

- [ ] **Step 3: Create `proteinclaw/core/agent/loop.py`**

```python
from __future__ import annotations
import json
from typing import AsyncGenerator
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY
from proteinclaw.core.agent.llm import call_llm, build_tools_schema
from proteinclaw.core.agent.prompt import build_system_prompt
from proteinclaw.core.agent.events import (
    Event, ToolCallEvent, ObservationEvent, TokenEvent, DoneEvent, ErrorEvent
)


async def run(
    query: str,
    history: list[dict],
    model: str,
    max_steps: int = 10,
) -> AsyncGenerator[Event, None]:
    """
    Run the ReAct agent loop. Yields typed Event objects.
    Consumer calls event.to_dict() to get the WebSocket-compatible dict.
    """
    tools = discover_tools()
    tools_schema = build_tools_schema(tools)
    system_prompt = build_system_prompt(tools)

    messages: list[dict] = (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": query}]
    )

    for step in range(max_steps):
        response_msg = call_llm(model=model, messages=messages, tools=tools_schema)

        if response_msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": response_msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response_msg.tool_calls
                ],
            })

            for tc in response_msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                yield ToolCallEvent(tool=tool_name, args=args)

                tool = tools.get(tool_name)
                if tool is None:
                    tool_result_dict = {"success": False, "error": f"Tool '{tool_name}' not found"}
                else:
                    result = tool.run(**args)
                    tool_result_dict = result.model_dump()

                yield ObservationEvent(tool=tool_name, result=tool_result_dict)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result_dict),
                })

        else:
            final_content = response_msg.content or ""
            for token in final_content.split(" "):
                yield TokenEvent(content=token + " ")
            yield DoneEvent()
            return

    yield ErrorEvent(message=f"Reached max_steps ({max_steps}) without a final answer.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/proteinclaw/test_loop.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/core/agent/loop.py tests/proteinclaw/test_loop.py
git commit -m "feat: migrate loop.py to core — async generator of typed Events"
```

---

## Task 5: Create Server Package + Migrate chat.py and tools.py

**Files:**
- Create: `proteinclaw/server/__init__.py`
- Create: `proteinclaw/server/main.py`
- Create: `proteinclaw/server/tools.py`
- Create: `proteinclaw/server/chat.py`
- Modify: `tests/proteinclaw/test_api.py`

- [ ] **Step 1: Update `tests/proteinclaw/test_api.py`**

Replace the entire file:

```python
import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from proteinclaw.server.main import app
from proteinclaw.core.agent.events import (
    TokenEvent, DoneEvent, ToolCallEvent, ObservationEvent, ErrorEvent
)


@pytest.mark.asyncio
async def test_get_tools():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_post_chat():
    async def mock_run(**kwargs):
        yield TokenEvent(content="Hello ")
        yield TokenEvent(content="world")
        yield DoneEvent()

    with patch("proteinclaw.server.chat.run", side_effect=mock_run):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={
                "message": "What is P04637?",
                "model": "gpt-4o",
                "history": [],
            })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "Hello" in data["reply"]


def test_websocket_chat():
    async def mock_run(**kwargs):
        yield ToolCallEvent(tool="uniprot", args={"accession_id": "P04637"})
        yield ObservationEvent(tool="uniprot", result={"success": True, "data": {"name": "TP53"}})
        yield TokenEvent(content="TP53 is ")
        yield TokenEvent(content="a tumor suppressor.")
        yield DoneEvent()

    with patch("proteinclaw.server.chat.run", side_effect=mock_run):
        client = TestClient(app)
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({
                "message": "What is P04637?",
                "model": "gpt-4o",
                "history": [],
            })
            events = []
            while True:
                event = ws.receive_json()
                events.append(event)
                if event["type"] in ("done", "error"):
                    break

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "observation" in types
    assert "token" in types
    assert "done" in types
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/test_api.py -v
```

Expected: `ModuleNotFoundError: No module named 'proteinclaw.server'`

- [ ] **Step 3: Create `proteinclaw/server/__init__.py`**

```bash
touch proteinclaw/server/__init__.py
```

- [ ] **Step 4: Create `proteinclaw/server/tools.py`**

```python
from fastapi import APIRouter
from proteinbox.tools.registry import discover_tools, TOOL_REGISTRY

router = APIRouter()

# Discover all tools once at import time (populates TOOL_REGISTRY)
discover_tools()


@router.get("/tools")
def list_tools():
    return {
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in TOOL_REGISTRY.values()
        ]
    }
```

- [ ] **Step 5: Create `proteinclaw/server/chat.py`**

```python
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from proteinclaw.core.agent.loop import run
from proteinclaw.core.agent.events import TokenEvent, ToolCallEvent, ErrorEvent
from proteinclaw.core.config import SUPPORTED_MODELS, settings

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    model: str = settings.default_model
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    model = request.model if request.model in SUPPORTED_MODELS else settings.default_model
    reply_parts = []
    tool_calls_log = []

    async for event in run(
        query=request.message,
        history=request.history,
        model=model,
    ):
        if isinstance(event, TokenEvent):
            reply_parts.append(event.content)
        elif isinstance(event, ToolCallEvent):
            tool_calls_log.append(event.to_dict())
        elif isinstance(event, ErrorEvent):
            reply_parts.append(f"\n[Error: {event.message}]")

    return ChatResponse(reply="".join(reply_parts).strip(), tool_calls=tool_calls_log)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            message = payload.get("message", "")
            model = payload.get("model", settings.default_model)
            history = payload.get("history", [])

            if model not in SUPPORTED_MODELS:
                model = settings.default_model

            async for event in run(query=message, history=history, model=model):
                await websocket.send_json(event.to_dict())

    except WebSocketDisconnect:
        pass
```

- [ ] **Step 6: Create `proteinclaw/server/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from proteinclaw.server.tools import router as tools_router
from proteinclaw.server.chat import router as chat_router

app = FastAPI(title="ProteinClaw", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tools_router)
app.include_router(chat_router)
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/proteinclaw/test_api.py -v
```

Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add proteinclaw/server/ tests/proteinclaw/test_api.py
git commit -m "feat: create server package with health endpoint and Event-based chat"
```

---

## Task 6: Update pyproject.toml + Delete Old Files

**Files:**
- Modify: `pyproject.toml`
- Delete: `proteinclaw/agent/`, `proteinclaw/api/`, `proteinclaw/main.py`, `proteinclaw/config.py`, `docker-compose.yml`

- [ ] **Step 1: Update `pyproject.toml`**

Add the `cli` optional dependency group and the `scripts` entry point. The final `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "proteinclaw"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "litellm>=1.40",
    "httpx>=0.27",
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
    "httpx[ws]>=0.27",
    "respx>=0.21",
]
cli = [
    "textual>=0.50",
]

[project.scripts]
proteinclaw = "proteinclaw.cli.app:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Run all tests to confirm nothing is broken before deleting**

```bash
pytest -v
```

Expected: all existing tests pass (including the new ones from tasks 1–5)

- [ ] **Step 3: Delete old directories and files**

```bash
rm -rf proteinclaw/agent/
rm -rf proteinclaw/api/
rm -f proteinclaw/main.py
rm -f proteinclaw/config.py
rm -f docker-compose.yml
```

- [ ] **Step 4: Run all tests again to confirm nothing broke**

```bash
pytest -v
```

Expected: all tests still pass

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove legacy agent/, api/, config.py; update pyproject.toml with CLI deps"
```

---

## Task 7: CLI Renderer

**Files:**
- Create: `proteinclaw/cli/__init__.py`
- Create: `proteinclaw/cli/renderer.py`
- Create: `tests/proteinclaw/test_renderer.py`

- [ ] **Step 1: Create `proteinclaw/cli/__init__.py`**

```bash
touch proteinclaw/cli/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `tests/proteinclaw/test_renderer.py`:

```python
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
```

- [ ] **Step 3: Run to verify failure**

```bash
pytest tests/proteinclaw/test_renderer.py -v
```

Expected: `ModuleNotFoundError: No module named 'proteinclaw.cli'`

- [ ] **Step 4: Create `proteinclaw/cli/renderer.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/proteinclaw/test_renderer.py -v
```

Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add proteinclaw/cli/ tests/proteinclaw/test_renderer.py
git commit -m "feat: add CLI renderer for stdout event output"
```

---

## Task 8: CLI — Interactive TUI and Entry Point

**Files:**
- Create: `proteinclaw/cli/app.py`

This task creates the Textual TUI and the `main()` function (the `proteinclaw` console script entry point). Testing the Textual TUI interactively is done by running `proteinclaw` after `pip install -e ".[cli]"`. Unit-testable logic (command parsing, model switching) is in `main()`.

- [ ] **Step 1: Install CLI dependencies**

```bash
pip install -e ".[cli]"
```

- [ ] **Step 2: Create `proteinclaw/cli/app.py`**

```python
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
```

- [ ] **Step 3: Smoke-test the CLI entry point**

```bash
# Non-interactive mode (no API key needed for import test)
proteinclaw --help
```

Expected: usage message printed, no import errors

- [ ] **Step 4: Commit**

```bash
git add proteinclaw/cli/app.py
git commit -m "feat: add Textual TUI and query subcommand to CLI"
```

---

## Task 9: Frontend Port Adaptation

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

The React app must read the port from `window.__BACKEND_PORT__` (injected by Tauri) rather than hardcoding 8000. In dev/browser mode, `window.__BACKEND_PORT__` is undefined, so it falls back to 8000.

- [ ] **Step 1: Add a TypeScript declaration for the injected global**

At the top of `frontend/src/hooks/useChat.ts`, add the declaration and update the `WS_URL` constant:

```typescript
// Add before the import block
declare global {
  interface Window {
    __BACKEND_PORT__?: number;
  }
}
```

Change line 4:

```typescript
// Before
const WS_URL = "ws://localhost:8000/ws/chat";

// After
const port = window.__BACKEND_PORT__ ?? 8000;
const WS_URL = `ws://localhost:${port}/ws/chat`;
```

- [ ] **Step 2: Verify the frontend still builds**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no TypeScript errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: read backend port from window.__BACKEND_PORT__ for Tauri support"
```

---

## Task 10: Tauri Project Setup

**Files:**
- Create: `src-tauri/` (via `cargo tauri init`)

**Prerequisites:** Install Rust and the Tauri CLI. On macOS: `brew install rust`; on Windows: install via rustup.rs. Then: `cargo install tauri-cli`.

- [ ] **Step 1: Install Tauri CLI v2**

```bash
cargo install tauri-cli --version "^2"
```

- [ ] **Step 2: Scaffold the Tauri project from the repo root**

```bash
cargo tauri init
```

When prompted:
- App name: `ProteinClaw`
- Window title: `ProteinClaw`
- Web assets path: `../frontend/dist`
- Dev server URL: `http://localhost:5173`
- Frontend dev command: `npm run dev`
- Frontend build command: `npm run build`

This creates `src-tauri/` with `Cargo.toml`, `tauri.conf.json`, and `src/main.rs`.

- [ ] **Step 3: Verify Tauri builds (empty shell)**

```bash
cargo tauri build --debug
```

Expected: debug build succeeds. The window will open but show a blank page or a "connection refused" error — that is expected at this stage.

- [ ] **Step 4: Commit the scaffolded Tauri project**

```bash
git add src-tauri/
git commit -m "feat: scaffold Tauri v2 desktop app shell"
```

---

## Task 11: Tauri — uv Sidecar and Python Server Lifecycle

**Files:**
- Create: `src-tauri/binaries/` (uv platform binaries)
- Modify: `src-tauri/tauri.conf.json`
- Modify: `src-tauri/Cargo.toml`
- Modify: `src-tauri/src/main.rs`

This task wires together the full startup sequence: bundled uv → first-launch venv setup → Python server → health poll → port injection → WebView.

- [ ] **Step 1: Download uv binaries into `src-tauri/binaries/`**

Visit https://github.com/astral-sh/uv/releases/latest and download:
- `uv-aarch64-apple-darwin.tar.gz` → extract `uv` → rename to `uv-aarch64-apple-darwin`
- `uv-x86_64-apple-darwin.tar.gz` → extract `uv` → rename to `uv-x86_64-apple-darwin`
- `uv-x86_64-pc-windows-msvc.zip` → extract `uv.exe` → rename to `uv-x86_64-pc-windows-msvc.exe`

Place all three in `src-tauri/binaries/`.

- [ ] **Step 2: Register uv as a sidecar in `tauri.conf.json`**

Add to the `bundle` section of `src-tauri/tauri.conf.json`:

```json
{
  "bundle": {
    "externalBin": ["binaries/uv"]
  }
}
```

- [ ] **Step 3: Add dependencies to `src-tauri/Cargo.toml`**

Add to `[dependencies]`:

```toml
ureq = "2"
```

(`tauri-plugin-shell` is NOT needed — we use `std::process::Command` directly.)

- [ ] **Step 4: Configure the main window to start hidden in `tauri.conf.json`**

Add/update the `windows` section so the window is hidden until the backend is ready (prevents React from running before `__BACKEND_PORT__` is injected):

```json
{
  "app": {
    "windows": [
      {
        "label": "main",
        "title": "ProteinClaw",
        "visible": false
      }
    ]
  }
}
```

- [ ] **Step 5: Rewrite `src-tauri/src/main.rs`**

```rust
// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::Manager;

struct PythonServer(Arc<Mutex<Option<Child>>>);

fn find_free_port(start: u16) -> u16 {
    for port in start..65535 {
        if std::net::TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return port;
        }
    }
    panic!("No free port found");
}

fn venv_exists(app_data_dir: &PathBuf) -> bool {
    app_data_dir.join("venv").join("pyvenv.cfg").exists()
}

fn uv_binary_path(resource_dir: &PathBuf) -> PathBuf {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return resource_dir.join("binaries").join("uv-aarch64-apple-darwin");
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return resource_dir.join("binaries").join("uv-x86_64-apple-darwin");
    #[cfg(target_os = "windows")]
    return resource_dir.join("binaries").join("uv-x86_64-pc-windows-msvc.exe");
}

fn poll_health(port: u16, timeout_secs: u64) -> bool {
    let url = format!("http://127.0.0.1:{}/health", port);
    let deadline = std::time::Instant::now() + Duration::from_secs(timeout_secs);
    while std::time::Instant::now() < deadline {
        if let Ok(resp) = ureq::get(&url).call() {
            if resp.status() == 200 {
                return true;
            }
        }
        thread::sleep(Duration::from_secs(1));
    }
    false
}

fn start_python_server(
    uv: &PathBuf,
    project_dir: &PathBuf,
    venv_dir: &PathBuf,
    port: u16,
) -> std::io::Result<Child> {
    Command::new(uv)
        .args([
            "run",
            "--project", project_dir.to_str().unwrap(),
            "--venv", venv_dir.to_str().unwrap(),
            "uvicorn",
            "proteinclaw.server.main:app",
            "--host", "127.0.0.1",
            "--port", &port.to_string(),
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let resource_dir = app.path().resource_dir().expect("resource dir");
            let app_data_dir = app.path().app_data_dir().expect("app data dir");
            let venv_dir = app_data_dir.join("venv");
            let uv = uv_binary_path(&resource_dir);
            let port = find_free_port(8000);

            // First-launch: create venv if absent
            if !venv_exists(&app_data_dir) {
                // TODO: show splash window here (future enhancement)
                Command::new(&uv)
                    .args([
                        "sync",
                        "--project", resource_dir.to_str().unwrap(),
                        "--venv", venv_dir.to_str().unwrap(),
                    ])
                    .status()
                    .expect("uv sync failed");
            }

            // Start Python server — retry up to 3 times before giving up
            let mut child: Option<Child> = None;
            for attempt in 1..=4 {
                match start_python_server(&uv, &resource_dir, &venv_dir, port) {
                    Ok(c) => {
                        if poll_health(port, 30) {
                            child = Some(c);
                            break;
                        }
                        // Server started but didn't become healthy — kill and retry
                        let mut c = c;
                        let _ = c.kill();
                    }
                    Err(e) => {
                        eprintln!("Attempt {}: failed to start Python server: {}", attempt, e);
                    }
                }
                if attempt == 4 {
                    // All retries exhausted — exit with a visible error
                    // (Native dialog deferred; eprintln is the minimum contract)
                    eprintln!("Python server failed to start after 4 attempts. Check logs.");
                    std::process::exit(1);
                }
                thread::sleep(Duration::from_secs(2));
            }

            let child = child.expect("child must be set if we reach here");
            let server_guard = Arc::new(Mutex::new(Some(child)));
            app.manage(PythonServer(server_guard.clone()));

            // Kill server on app exit
            let sg = server_guard.clone();
            app.on_window_event(move |_window, event| {
                if let tauri::WindowEvent::Destroyed = event {
                    if let Ok(mut guard) = sg.lock() {
                        if let Some(mut child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            });

            // Server is healthy — inject port and show the window
            // Window was created hidden (visible: false in tauri.conf.json),
            // so __BACKEND_PORT__ is set before any React code runs.
            if let Some(window) = app.get_webview_window("main") {
                let script = format!("window.__BACKEND_PORT__ = {};", port);
                let _ = window.eval(&script);
                let _ = window.show();
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}
```

- [ ] **Step 6: Build and test the desktop app**

```bash
# Build the frontend first
cd frontend && npm run build && cd ..

# Run in dev mode (opens a window)
cargo tauri dev
```

Expected:
- First launch: `uv sync` runs, venv created at `~/.proteinclaw/venv` (or platform equivalent)
- Python server starts
- Window opens showing the React UI
- WebSocket connects and chat works

- [ ] **Step 7: Commit**

```bash
git add src-tauri/ frontend/
git commit -m "feat: Tauri desktop app with uv sidecar and Python server lifecycle"
```

---

## Task 12: Tauri — Package for Distribution

**Files:**
- No new files; configure existing `src-tauri/tauri.conf.json`

- [ ] **Step 1: Configure bundle identifiers in `tauri.conf.json`**

Update the `bundle` section:

```json
{
  "bundle": {
    "active": true,
    "targets": "all",
    "identifier": "com.proteinclaw.app",
    "icon": ["icons/icon.png"],
    "externalBin": ["binaries/uv"]
  }
}
```

- [ ] **Step 2: Build release packages**

On macOS:
```bash
cargo tauri build
```

On Windows (run from a Windows machine or CI):
```bash
cargo tauri build
```

Expected output:
- macOS: `src-tauri/target/release/bundle/dmg/ProteinClaw_*.dmg`
- Windows: `src-tauri/target/release/bundle/nsis/ProteinClaw_*_setup.exe`

- [ ] **Step 3: Smoke-test the packaged app**

Install the `.dmg` / `.exe` and launch. Verify:
1. App opens without needing Python or uv installed
2. First-launch installs deps (uv creates venv)
3. Subsequent launches start immediately
4. Chat works end-to-end

- [ ] **Step 4: Commit**

```bash
git add src-tauri/tauri.conf.json
git commit -m "feat: configure Tauri bundle for macOS and Windows distribution"
```

---

## Final Verification

- [ ] **Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass

- [ ] **Verify CLI works**

```bash
pip install -e ".[cli]"
proteinclaw --help
proteinclaw query "What is P04637?"   # requires a valid API key
```

- [ ] **Verify dev server works (no Tauri)**

```bash
uvicorn proteinclaw.server.main:app --reload
# In another terminal:
cd frontend && npm run dev
# Open http://localhost:5173
```

- [ ] **Commit any final fixes**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```
