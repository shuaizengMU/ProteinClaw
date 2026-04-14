# Nanobot Integration Design

**Date:** 2026-04-14  
**Branch:** dev-claw  
**Goal:** Replace the custom ReAct agent loop with nanobot as the long-term agent middleware. Reduce maintenance burden while keeping the frontend and WebSocket server unchanged.

---

## Background

ProteinClaw currently runs a hand-written ReAct loop (`proteinclaw/core/agent/loop.py`) with a custom LLM abstraction, prompt builder, and event types. This works but requires ongoing maintenance as requirements evolve.

nanobot (https://github.com/HKUDS/nanobot) is an ultra-lightweight personal AI agent framework that provides: an agent loop, tool registry, memory persistence, lifecycle hooks, and a Python SDK. Using it as middleware eliminates the need to maintain the loop, LLM abstraction, and prompt logic.

---

## Decisions

| Question | Decision |
|---|---|
| Primary motivation | Reduce maintenance cost |
| Frontend changes | None — keep existing WebSocket event protocol |
| Tool migration | Wrap sync tools with `asyncio.to_thread` (no refactor) |
| Memory | Enable nanobot memory (SOUL.md, USER.md, history.jsonl) |
| Future development | All new agent features built on nanobot |

---

## Architecture

### Files Deleted

```
proteinclaw/core/agent/loop.py      ← replaced by nanobot
proteinclaw/core/agent/llm.py       ← replaced by nanobot providers
proteinclaw/core/agent/prompt.py    ← replaced by nanobot SOUL.md
```

`events.py` is deleted. All WebSocket events are emitted as plain dicts directly from `WebSocketAdapter`.

### Files Added

```
proteinclaw/core/nanobot/
├── __init__.py
├── config.py      ← generates nanobot config.json from env vars at startup
├── tools.py       ← wraps all 35 proteinbox tools as nanobot Tool subclasses
├── adapter.py     ← AgentHook that maps nanobot events → existing WS protocol
└── instance.py    ← singleton Nanobot, initialized at app startup
```

### Files Modified

```
proteinclaw/server/chat.py     ← ~10 lines: swap old loop.run() for nanobot bot.run()
pyproject.toml                 ← add nanobot>=0.1.5 dependency
```

### Files Untouched

```
frontend/                      ← zero changes
proteinclaw/server/main.py     ← zero changes
proteinbox/                    ← zero changes (all 35 tools preserved as-is)
```

---

## Data Flow

```
Frontend WebSocket
    │ {message, model, history, api_key}
    ▼
chat.py (FastAPI WebSocket handler)
    │ create WebSocketAdapter(websocket.send_json)
    │ get_nanobot_instance()
    ▼
bot.run(message, session_key="proj:conv", hooks=[WebSocketAdapter])
    │
    ▼ nanobot agent loop (internal)
    ├── on_stream(delta)          → {"type": "token",       "content": delta}
    ├── before_execute_tools()    → {"type": "tool_call",   "tool": name, "args": args}
    └── after_iteration()         → {"type": "observation", "tool": name, "result": {...}}
    
    after bot.run() returns:
    └── send {"type": "done"}
```

---

## Component Details

### config.py

Generates a nanobot-compatible `config.json` at app startup from existing env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) and Tauri `app_data_dir`.

Key config options:
- `workspace`: `<app_data_dir>/nanobot-workspace/`
- `tools.filesystem`: `false` — disable nanobot built-in file tools
- `tools.shell`: `false` — disable shell execution (security)
- `tools.web`: `false` — disable nanobot built-in web tools (use proteinbox tools instead)
- `memory.enabled`: `true`

### tools.py

Single generic wrapper class converts all proteinbox tools to nanobot format:

```python
class ProteinboxToolWrapper(Tool):
    def __init__(self, protein_tool: ProteinTool): ...
    
    @property
    def name(self) -> str: return self._tool.name
    @property
    def description(self) -> str: return self._tool.description
    @property
    def parameters(self) -> dict: return self._tool.parameters

    async def execute(self, **kwargs) -> str:
        result = await asyncio.to_thread(self._tool.run, **kwargs)
        return json.dumps(result.model_dump())


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in discover_tools().values():
        registry.register(ProteinboxToolWrapper(tool))
    return registry
```

No changes to proteinbox tools. New tools added to proteinbox are automatically registered.

### adapter.py

`WebSocketAdapter(AgentHook)` maps nanobot lifecycle events to the existing frontend protocol:

| Hook method | Frontend event emitted |
|---|---|
| `on_stream(ctx, delta)` | `{"type": "token", "content": delta}` |
| `before_execute_tools(ctx)` | `{"type": "tool_call", "tool": name, "args": args}` per tool |
| `after_iteration(ctx, response)` | `{"type": "observation", "tool": name, "result": {...}}` per result — exact field on `ctx` carrying tool results to be confirmed against nanobot `AgentHookContext` API during implementation |
| after `bot.run()` returns | `{"type": "done"}` |
| exception caught | `{"type": "error", "message": str(e)}` |

### instance.py

Singleton `Nanobot` instance initialized once at FastAPI startup. Provides `get_nanobot_instance()` for use in `chat.py`.

### Memory (SOUL.md)

Initial `SOUL.md` content written to workspace on first run:

```markdown
You are ProteinClaw, an expert AI agent for protein bioinformatics research.
You have access to 35 specialized tools covering protein annotation, structure,
variants, disease, pathways, expression, genomics, and literature databases
including UniProt, BLAST, AlphaFold, PDB, ClinVar, GTEx, and more.
Always chain tools intelligently to answer complex research questions thoroughly.
```

`USER.md` and `history.jsonl` are managed automatically by nanobot.

### session_key

Format: `"{project_id}:{conversation_id}"` — gives each conversation an independent nanobot memory context.

---

## Dependency

```toml
# pyproject.toml
"nanobot>=0.1.5",
```

Note: nanobot Python SDK is marked experimental until v0.1.5. If the version is not yet released at implementation time, pin to the latest available and note any API differences.

---

## What Is NOT Changing

- Frontend event protocol (`token`, `tool_call`, `observation`, `done`, `error`)
- All 35 proteinbox tools — logic, parameters, return types
- FastAPI server structure and endpoints
- Tauri app, build scripts, icons

---

## Future Development on nanobot

Once integrated, new capabilities should be built using nanobot primitives:
- **Skills**: Add domain-specific skills as `SKILL.md` files under `proteinclaw/skills/`
- **Subagents**: Parallel research tasks via nanobot's subagent mechanism
- **Memory**: Leverage USER.md for personalized research context
- **Cron**: Scheduled protein monitoring tasks via nanobot's cron system
