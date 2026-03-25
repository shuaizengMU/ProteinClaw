# ProteinClaw Architecture Redesign

**Date:** 2026-03-25
**Status:** Approved
**Supersedes:** `2026-03-24-proteinclaw-design.md` (MVP design)

## Background

The original MVP design used Docker Compose for deployment with a FastAPI backend and React frontend. This redesign replaces Docker with a local-first architecture that:

1. Runs as a native desktop app (Windows + macOS) via Tauri
2. Supports an interactive CLI with full feature parity to the GUI
3. Requires zero pre-installed dependencies (uv bundled in the app)
4. Follows a ComfyUI-style local server + browser UI pattern

## Architecture Overview

Three execution paths share the same core agent logic:

```
GUI path:   Tauri (Rust) → starts Python server → WebView → React → WebSocket → core/agent
CLI path:   $ proteinclaw  →  cli/app.py  →  direct import core/agent
Dev path:   $ uvicorn proteinclaw.server.main:app  →  browser at localhost:8000
```

## Repository Structure

```
ProteinClaw/
├── proteinbox/                  # Tool layer (unchanged)
│   └── tools/
│       ├── __init__.py
│       ├── registry.py
│       ├── uniprot.py
│       └── blast.py
│
├── proteinclaw/
│   ├── core/                    # Pure Python core — no web/CLI dependencies
│   │   ├── __init__.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── events.py        # Event base class + all event dataclasses
│   │   │   ├── loop.py          # ReAct loop (migrated from agent/)
│   │   │   ├── llm.py
│   │   │   └── prompt.py
│   │   └── config.py            # Shared config
│   │
│   ├── server/                  # FastAPI entry point (renamed from api/)
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory (was proteinclaw/main.py)
│   │   ├── chat.py              # POST /chat, WebSocket /ws/chat, GET /health
│   │   └── tools.py             # GET /tools
│   │
│   └── cli/                     # Interactive terminal entry point (new)
│       ├── __init__.py
│       ├── app.py               # Textual main loop
│       └── renderer.py          # Event → terminal rendering
│
├── src-tauri/                   # Tauri Rust shell (new)
│   ├── src/
│   │   └── main.rs              # Python server lifecycle + WebView
│   ├── binaries/
│   │   └── uv-*                 # Bundled uv binaries (per platform)
│   └── tauri.conf.json
│
├── frontend/                    # React frontend (unchanged)
│   └── src/
│
├── pyproject.toml               # Adds CLI entry point + optional cli deps
└── .env.example                 # No docker-compose.yml
```

All `__init__.py` files are standard empty package markers. They are shown in the structure above but omitted from implementation details below for brevity.

## Core Layer

### Principle

`proteinclaw/core/` contains pure Python logic with **no imports from FastAPI, WebSocket libraries, or Textual**. It can be imported and tested independently of any I/O layer.

### Event Types (`proteinclaw/core/agent/events.py`)

All events share a base dataclass with a `to_dict()` method. The `type` field maps 1:1 to the existing WebSocket JSON protocol.

```python
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

| Event class | JSON `type` field | Payload |
|-------------|-------------------|---------|
| `ThinkingEvent` | `thinking` | `content: str` |
| `ToolCallEvent` | `tool_call` | `tool: str`, `args: dict` |
| `ObservationEvent` | `observation` | `tool: str`, `result: Any` |
| `TokenEvent` | `token` | `content: str` |
| `DoneEvent` | `done` | — |
| `ErrorEvent` | `error` | `message: str` |

### Agent Loop Interface (`proteinclaw/core/agent/loop.py`)

The agent loop is an async generator function. This is the single shared interface consumed by both the server and the CLI:

```python
from typing import AsyncGenerator
from proteinclaw.core.agent.events import Event

async def run(
    query: str,
    history: list[dict],
    model: str,
    max_steps: int = 10,
) -> AsyncGenerator[Event, None]:
    yield ThinkingEvent(content="...")
    yield ToolCallEvent(tool="uniprot", args={"id": "P04637"})
    yield ObservationEvent(tool="uniprot", result={...})
    yield TokenEvent(content="TP53 是...")
    yield DoneEvent()
```

**Migration notes from existing `run_agent`:**
- Renamed: `run_agent` → `run`
- Renamed parameter: `message` → `query`
- `max_steps: int = 10` is kept (existing tests depend on it)
- Internal `yield` replaces the current inline streaming dict construction
- All ReAct logic (Thought → Action → Observation loop, error handling) is unchanged

## Server Layer

`proteinclaw/server/` (renamed from `proteinclaw/api/`) consumes the core async generator and pushes events over WebSocket. The existing multi-turn `while True` loop is preserved so one WebSocket connection handles the full conversation session:

```python
# proteinclaw/server/chat.py (simplified)

@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    while True:
        payload = await websocket.receive_json()
        async for event in run(
            query=payload["message"],
            history=payload["history"],
            model=payload["model"],
        ):
            await websocket.send_json(event.to_dict())
```

### `/health` Endpoint

Required by the Tauri startup sequence to know when the server is ready. Added to `proteinclaw/server/chat.py` (or a new `health.py`):

```python
@router.get("/health")
async def health():
    return {"status": "ok"}
```

The Tauri Rust shell polls `GET localhost:{port}/health` with a 1-second interval until it receives `200 OK`, then opens the WebView.

### Port Communication to Frontend

The server starts on port **8000** by default. If port 8000 is occupied, Tauri picks the next available port and passes it to the WebView via a Tauri JS API injection before opening the window:

```rust
// src-tauri/src/main.rs
window.eval(&format!("window.__BACKEND_PORT__ = {};", port)).unwrap();
```

The React app reads `window.__BACKEND_PORT__ ?? 8000` to construct the WebSocket URL. In dev mode (no Tauri), the default 8000 is always used and no injection occurs.

All existing API endpoints (`GET /tools`, `POST /chat`, `WebSocket /ws/chat`) and the WebSocket JSON protocol are preserved. The React frontend otherwise requires no changes.

## CLI Layer

### Technology

**Textual** (pure Python TUI framework) for the interactive interface. Installed as an optional dependency group so server-only users do not pull it in:

```toml
# pyproject.toml
[project.optional-dependencies]
cli = ["textual>=0.50"]

[project.scripts]
proteinclaw = "proteinclaw.cli.app:main"
```

Install with CLI support: `pip install "proteinclaw[cli]"` or `uv pip install ".[cli]"`.

### Entry Points

```bash
proteinclaw                          # Interactive TUI (multi-turn)
proteinclaw query "分析 P04637"      # Single query, print to stdout, exit
```

### Interactive TUI Layout

```
┌─────────────────────────────────────┐
│  ProteinClaw  [model: gpt-4o ▼]     │  ← status bar + model selector
├─────────────────────────────────────┤
│                                     │
│  > 分析 P04637                      │  ← conversation history
│                                     │
│  ▶ [tool: uniprot] P04637           │  ← collapsible tool call
│    └ TP53_HUMAN, 393 aa...          │
│                                     │
│  TP53 是人类最重要的肿瘤抑制蛋白... │  ← streaming output
│                                     │
├─────────────────────────────────────┤
│  > _                                │  ← input box
└─────────────────────────────────────┘
```

### Non-Interactive `query` Subcommand

`proteinclaw query "<text>"` runs a single query without launching the TUI:
- Streams tokens to stdout as they arrive (same progressive output as TUI)
- Tool call events printed as `[tool: uniprot] args...` inline
- Exits with code 0 on `DoneEvent`, code 1 on `ErrorEvent`
- Uses `cli/renderer.py` in a plain-stdout mode (no Textual widgets)

### CLI Commands (inside TUI)

| Command | Action |
|---------|--------|
| `/model <name>` | Switch LLM model |
| `/tools` | List registered tools |
| `/clear` | Clear conversation history |
| `/exit` | Exit |

### Renderer

`cli/renderer.py` maps each Event type to either a Textual widget update (TUI mode) or a stdout print (non-interactive mode). The same six event types are handled in both cases.

## Tauri Desktop App

### First-Launch Detection

Tauri checks for `~/.proteinclaw/venv/pyvenv.cfg`. If absent, the first-launch installation flow runs (shows splash screen, calls `uv sync`). If present, the server starts immediately.

### Startup Sequence

```
User launches ProteinClaw.app
    ↓
Tauri (Rust) starts
    ↓
Check ~/.proteinclaw/venv/pyvenv.cfg
    ├─ absent → show splash screen, run: bundled-uv sync --project . → venv created
    └─ present → skip installation
    ↓
Find available port (default 8000, increment if occupied)
    ↓
Start Python server: bundled-uv run --project {resource_dir} uvicorn proteinclaw.server.main:app --port {port}
    (resource_dir = directory containing pyproject.toml, resolved by Tauri at build time; not cwd,
     which on macOS .app bundles defaults to / and must not be relied upon)
    ↓
Poll GET localhost:{port}/health every 1s until 200 OK
    ↓
Inject window.__BACKEND_PORT__ = {port} into WebView
    ↓
Open WebView → user sees React UI
```

### Rust Shell Responsibilities (`src-tauri/src/main.rs`)

1. Manage Python server subprocess lifecycle (start on app open, kill on app close)
2. Detect port conflicts and auto-select an available port
3. Show splash screen with progress during first-launch dependency installation
4. Crash recovery: restart the Python subprocess up to 3 times; on the 4th failure show a native error dialog and offer to open the log file. *(Detailed crash recovery UX is deferred; this is the minimum contract.)*

### Bundled uv Binaries

uv is a single static binary (~10MB). Tauri's sidecar mechanism bundles platform-specific binaries:

| Platform | Binary name in `src-tauri/binaries/` |
|----------|---------------------------------------|
| macOS arm64 | `uv-aarch64-apple-darwin` |
| macOS x86_64 | `uv-x86_64-apple-darwin` |
| Windows x86_64 | `uv-x86_64-pc-windows-msvc.exe` |

Python itself is managed by uv (auto-downloaded on first run to `~/.proteinclaw/venv`). No Python or uv installation is required on the user's machine.

### Package Output

| Platform | Format | Estimated size |
|----------|--------|----------------|
| macOS | `.dmg` | ~20MB |
| Windows | `.exe` (NSIS installer) | ~15MB |

Python dependencies (~500MB installed) are downloaded on first launch and cached at `~/.proteinclaw/venv`.

## Migration Scope

### Unchanged

- `proteinbox/tools/` — tool layer, zero changes
- `frontend/` — React frontend, zero changes (reads `window.__BACKEND_PORT__ ?? 8000`)
- WebSocket JSON event protocol — same format

### Migrated (move + specific changes)

| From | To | Changes |
|------|----|---------|
| `proteinclaw/agent/loop.py` | `proteinclaw/core/agent/loop.py` | Rename `run_agent` → `run`; rename param `message` → `query`; convert internal streaming to `yield Event`; keep `max_steps` |
| `proteinclaw/agent/llm.py` | `proteinclaw/core/agent/llm.py` | Path only |
| `proteinclaw/agent/prompt.py` | `proteinclaw/core/agent/prompt.py` | Path only |
| `proteinclaw/api/chat.py` | `proteinclaw/server/chat.py` | Replace direct streaming with `async for event in run(...)` + add `/health` endpoint |
| `proteinclaw/api/tools.py` | `proteinclaw/server/tools.py` | Path only |
| `proteinclaw/main.py` | `proteinclaw/server/main.py` | Path only |
| `proteinclaw/config.py` | `proteinclaw/core/config.py` | Path only |
| `tests/proteinclaw/test_loop.py` | Same path | Update import: `proteinclaw.agent.loop` → `proteinclaw.core.agent.loop`; update call: `run_agent(message=...)` → `run(query=...)`; note parameter order change (`model` and `history` swap — safe because call sites use keyword args); update patch strings: `"proteinclaw.agent.loop.call_llm"` → `"proteinclaw.core.agent.loop.call_llm"` |
| `tests/proteinclaw/test_llm.py` | Same path | Update patch string: `"proteinclaw.agent.llm.litellm.completion"` → `"proteinclaw.core.agent.llm.litellm.completion"` |
| `tests/proteinclaw/test_*.py` | Same paths | Update all imports from `proteinclaw.agent.*` / `proteinclaw.config` to `proteinclaw.core.*` |
| `tests/proteinclaw/test_api.py` | Same path | `from proteinclaw.main import app` → `from proteinclaw.server.main import app` |
| `tests/proteinclaw/test_api.py` | Same path | `patch("proteinclaw.api.chat.run_agent", ...)` → `patch("proteinclaw.server.chat.run", ...)` in `test_post_chat` and `test_websocket_chat` |

### New

- `proteinclaw/core/agent/events.py` — Event base class + all event dataclasses
- `proteinclaw/cli/` — Textual TUI (`app.py`, `renderer.py`)
- `src-tauri/` — Rust shell
- uv sidecar binaries in `src-tauri/binaries/`

### Deleted

- `docker-compose.yml`
- `proteinclaw/agent/` directory (contents moved to `proteinclaw/core/agent/`)
- `proteinclaw/api/` directory (contents moved to `proteinclaw/server/`)

## Out of Scope

- Node-based visual workflow editor (deferred, to be designed separately)
- Linux desktop packaging
- Auto-update mechanism for the desktop app
- Multi-user / remote server deployment
- Detailed crash recovery UX beyond the 3-retry minimum
