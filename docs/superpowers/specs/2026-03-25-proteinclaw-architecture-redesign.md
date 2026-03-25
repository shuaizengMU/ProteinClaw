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
│       ├── registry.py
│       ├── uniprot.py
│       └── blast.py
│
├── proteinclaw/
│   ├── core/                    # Pure Python core — no web/CLI dependencies
│   │   ├── agent/
│   │   │   ├── loop.py          # ReAct loop (migrated from agent/)
│   │   │   ├── llm.py
│   │   │   └── prompt.py
│   │   └── config.py            # Shared config
│   │
│   ├── server/                  # FastAPI entry point (renamed from api/)
│   │   ├── main.py
│   │   ├── chat.py
│   │   └── tools.py
│   │
│   └── cli/                     # Interactive terminal entry point (new)
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
├── pyproject.toml               # Adds CLI entry point
└── .env.example                 # No docker-compose.yml
```

## Core Layer

### Principle

`proteinclaw/core/` contains pure Python logic with **no imports from FastAPI, WebSocket libraries, or Textual**. It can be imported and tested independently of any I/O layer.

### Agent Loop Interface

The agent loop exposes an async generator. This is the single shared interface consumed by both the server and the CLI:

```python
# proteinclaw/core/agent/loop.py

async def run(
    query: str,
    history: list[dict],
    model: str,
) -> AsyncIterator[Event]:
    yield ThinkingEvent(content="...")
    yield ToolCallEvent(tool="uniprot", args={"id": "P04637"})
    yield ObservationEvent(tool="uniprot", result={...})
    yield TokenEvent(content="TP53 是...")
    yield DoneEvent()
```

### Event Types

Strongly-typed dataclasses mapping 1:1 to the existing WebSocket JSON protocol:

| Event class | JSON `type` field | Payload |
|-------------|-------------------|---------|
| `ThinkingEvent` | `thinking` | `content: str` |
| `ToolCallEvent` | `tool_call` | `tool: str`, `args: dict` |
| `ObservationEvent` | `observation` | `tool: str`, `result: Any` |
| `TokenEvent` | `token` | `content: str` |
| `DoneEvent` | `done` | — |
| `ErrorEvent` | `error` | `message: str` |

### Migration from Existing Code

`proteinclaw/agent/loop.py` is moved to `proteinclaw/core/agent/loop.py`. The only code change is converting the internal streaming output to `yield` statements. All ReAct logic (Thought → Action → Observation loop, `max_steps`, error handling) is preserved unchanged.

## Server Layer

`proteinclaw/server/` (renamed from `proteinclaw/api/`) consumes the core async generator and pushes events over WebSocket:

```python
# proteinclaw/server/chat.py

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    payload = await websocket.receive_json()
    async for event in agent.run(payload["message"], payload["history"], payload["model"]):
        await websocket.send_json(event.to_dict())
```

All existing API endpoints (`GET /tools`, `POST /chat`, `WebSocket /ws/chat`) and the WebSocket JSON protocol are preserved. The React frontend requires no changes.

## CLI Layer

### Technology

**Textual** (pure Python TUI framework) for the interactive interface.

### Entry Points

```bash
proteinclaw                          # Interactive TUI (multi-turn)
proteinclaw query "分析 P04637"      # Single query, print result, exit
```

### TUI Layout

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

### CLI Commands

| Command | Action |
|---------|--------|
| `/model <name>` | Switch LLM model |
| `/tools` | List registered tools |
| `/clear` | Clear conversation history |
| `/exit` | Exit |

### Renderer

`cli/renderer.py` maps each Event type to a Textual widget update, parallel to the React frontend's WebSocket event handler. The same six event types are handled.

## Tauri Desktop App

### Startup Sequence

```
User launches ProteinClaw.app
    ↓
Tauri (Rust) starts
    ↓
Uses bundled uv binary (no system uv required)
    ↓
uv creates venv at ~/.proteinclaw/venv and installs dependencies
(first launch ~30s; subsequent launches skip this step)
    ↓
Starts Python server subprocess: uv run uvicorn proteinclaw.server.main:app
    ↓
Polls localhost:{port}/health until ready
    ↓
Opens WebView pointing to localhost:{port}
    ↓
User sees React UI
```

### Rust Shell Responsibilities (`src-tauri/src/main.rs`)

1. Manage Python server subprocess lifecycle (start, stop, crash recovery)
2. Detect port conflicts and auto-select an available port
3. Show splash screen with progress during first-launch dependency installation
4. Kill Python subprocess on app close

### Bundled uv Binaries

uv is a single static binary (~10MB). Tauri's sidecar mechanism bundles platform-specific binaries:

| Platform | Binary name |
|----------|-------------|
| macOS arm64 | `uv-aarch64-apple-darwin` |
| macOS x86_64 | `uv-x86_64-apple-darwin` |
| Windows x86_64 | `uv-x86_64-pc-windows-msvc.exe` |

Python itself is managed by uv (auto-downloaded on first run). No Python installation required on the user's machine.

### Package Output

| Platform | Format | Estimated size |
|----------|--------|----------------|
| macOS | `.dmg` | ~20MB |
| Windows | `.exe` (NSIS installer) | ~15MB |

Python dependencies are installed to `~/.proteinclaw/venv` on first launch and reused on subsequent launches.

## Migration Scope

### Unchanged

- `proteinbox/tools/` — tool layer, zero changes
- `frontend/` — React frontend, zero changes
- WebSocket JSON event protocol — same format

### Migrated (move + minor changes)

| From | To | Change |
|------|----|--------|
| `proteinclaw/agent/` | `proteinclaw/core/agent/` | `loop.py` converted to async generator |
| `proteinclaw/api/` | `proteinclaw/server/` | Consumes `async for event` instead of direct streaming |
| `proteinclaw/config.py` | `proteinclaw/core/config.py` | Path only |

### New

- `proteinclaw/cli/` — Textual TUI (new)
- `src-tauri/` — Rust shell (new)
- uv sidecar binaries

### Deleted

- `docker-compose.yml`

## Out of Scope

- Node-based visual workflow editor (deferred, to be designed separately)
- Linux desktop packaging
- Auto-update mechanism for the desktop app
- Multi-user / remote server deployment
