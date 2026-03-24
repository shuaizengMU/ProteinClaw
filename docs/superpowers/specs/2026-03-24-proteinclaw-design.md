# ProteinClaw MVP Design Spec

**Date:** 2026-03-24
**Status:** Approved

## Background

Protein science lacks a unified computational platform analogous to Seurat (single-cell) or DNAStar (DNA workflows). This project builds two tightly coupled systems in a single mono-repo:

- **ProteinBox**: A unified bioinformatics platform integrating ~100 protein analysis tools and ~30 databases via standardized APIs and containers.
- **ProteinClaw**: An AI agent-driven interface that accepts natural language goals and autonomously orchestrates ProteinBox tools into executable analysis workflows.

## MVP Scope

Validate the end-to-end chain: natural language input → agent tool calls → result display.

**MVP scenario:** User provides a UniProt Accession ID → Agent queries structure/functional annotation → Agent generates an analysis summary.

No advanced features (skill capture, literature-augmented validation, evolutionary workflow optimization) in MVP.

## Architecture

### Repo Structure

```
ProteinClaw/
├── proteinbox/               # Protein analysis tool & database layer
│   ├── tools/
│   │   ├── registry.py       # Tool base class (ProteinTool) + auto-discovery
│   │   ├── uniprot.py        # UniProt query tool (MVP)
│   │   └── blast.py          # BLAST tool (MVP)
│   └── __init__.py
├── proteinclaw/              # FastAPI backend + AI agent
│   ├── agent/
│   │   ├── loop.py           # ReAct agent main loop
│   │   ├── llm.py            # LiteLLM wrapper, multi-model routing
│   │   └── prompt.py         # System prompt templates
│   ├── api/
│   │   ├── chat.py           # POST /chat, WebSocket /ws/chat
│   │   └── tools.py          # GET /tools
│   └── config.py             # LLM config, API keys
├── frontend/                 # React frontend
│   └── src/
│       ├── components/
│       │   ├── ChatWindow.tsx
│       │   ├── ToolCallCard.tsx
│       │   └── ModelSelector.tsx
└── docker-compose.yml
```

### Data Flow

```
User input → FastAPI WebSocket → ReAct Loop → LiteLLM
                                      ↕ tool_call
                                 proteinbox.tools.registry → External APIs (UniProt, NCBI)
                                      ↕ observation
                                 Next LLM inference → Final answer → Stream to frontend
```

## ReAct Agent Core

The agent follows the standard ReAct pattern (Thought → Action → Observation) implemented as a simple loop:

```python
while not done and steps < max_steps:
    response = llm.chat(messages)           # Thought + Action
    if response.has_tool_call:
        result = tool_registry.invoke(tool_name, args)
        messages.append(observation(result))  # Observation
    else:
        done = True                         # Final Answer
```

**Default `max_steps`:** 10

**Error handling:**
- Tool failure → error returned as Observation; LLM decides whether to retry or change strategy
- `max_steps` exceeded → return partial results with explanation
- LLM API timeout → surface user-visible error message

**Streaming:** LiteLLM `stream=True`; tokens pushed incrementally over WebSocket. Tool call events pushed as discrete messages for frontend rendering.

## ProteinBox — Tool Layer

### ToolResult Type

```python
class ToolResult(BaseModel):
    success: bool
    data: Any                    # Raw structured data (dict/list) for LLM observation
    display: Optional[str]       # Human-readable summary for frontend rendering
    error: Optional[str]         # Error message if success=False
```

### Tool Base Class

```python
class ProteinTool(BaseModel):
    name: str
    description: str             # Injected into system prompt so LLM knows when to use it
    parameters: JsonSchemaDict   # OpenAI function-calling compatible JSON Schema, e.g.:
                                 # {"type": "object",
                                 #  "properties": {"id": {"type": "string", "description": "UniProt accession"}},
                                 #  "required": ["id"]}

    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
```

**Tool auto-discovery:** At startup, `registry.py` imports all modules in `proteinbox/tools/` via `pkgutil.iter_modules`. Each module decorated with `@register_tool` is added to a global `TOOL_REGISTRY` dict keyed by `name`. New tools require only creating a new file in `proteinclaw/tools/` — no `__init__.py` edits needed.

New tools are registered via `@register_tool` decorator and auto-discovered at startup. No additional configuration required.

### MVP Tools

| Tool | Input | API | Output |
|------|-------|-----|--------|
| `UniProtTool` | UniProt Accession ID (e.g. `P04637`) | `https://rest.uniprot.org/uniprotkb/{id}.json` | Name, function, GO terms, sequence length, species |
| `BLASTTool` | Protein sequence (FASTA) | NCBI BLAST E-utilities (async submit → poll) | Top-N hits with E-value and coverage |

**BLASTTool async polling behavior (MVP):** The tool submits the job synchronously and polls NCBI internally until completion (blocking `run()` call). Timeout: 120 seconds. On timeout, returns `ToolResult(success=False, error="BLAST search timed out after 120s")`. The ReAct loop treats this as an Observation and lets the LLM decide next steps. Intermediate polling status is not streamed to the frontend in MVP.

**API key requirements:**
- UniProt, PDB, InterPro: public, no key needed
- NCBI E-utilities: `NCBI_API_KEY` optional (higher rate limit with key)
- All keys managed via `.env` + `config.py`; never hardcoded

## API Interface

| Endpoint | Description |
|----------|-------------|
| `GET /tools` | List all registered tools with names and descriptions |
| `POST /chat` | Non-streaming chat (for testing) |
| `WebSocket /ws/chat` | Streaming chat session |

**`POST /chat` schema:**
```json
// Request
{"message": "What is P04637?", "model": "gpt-4o", "history": []}

// Response
{"reply": "P04637 is TP53...", "tool_calls": [...]}
```

**Authentication / CORS:** No authentication required for MVP (local development tool). FastAPI CORS middleware configured to allow all origins (`*`) in development. Production deployment policy is out of scope for MVP.

**Conversation history ownership:** The backend is stateless per WebSocket connection. The client (`ChatWindow`) maintains the full message history and sends it with each request:
- WebSocket: history included as `"history"` field in the initial message payload
- `POST /chat`: history sent as `"history"` array in request body
- The backend constructs the LLM message list from the provided history on each turn

**Model selection:** `ModelSelector` persists selection in `localStorage`. On each WebSocket message send (and `POST /chat` request), the selected model name is included as `"model"` in the payload. The backend `llm.py` resolves it against `SUPPORTED_MODELS` in `config.py`.

### WebSocket Event Types

```json
{"type": "thinking",    "content": "I need to look up..."}
{"type": "tool_call",   "tool": "uniprot", "args": {"id": "P04637"}}
{"type": "observation", "tool": "uniprot", "result": {...}}
{"type": "token",       "content": "该蛋白是..."}
{"type": "done"}
{"type": "error",       "message": "..."}
```

**Frontend rendering per event type:**
- `thinking`: rendered as a dimmed italic line within `ChatWindow` inline with the response stream (not in `ToolCallCard`)
- `tool_call` + `observation`: rendered together as a collapsible `ToolCallCard` in `ChatWindow`
- `token`: appended to the current assistant message bubble in `ChatWindow`
- `done`: finalizes the current assistant message bubble
- `error`: rendered as a red error banner in `ChatWindow`

## Frontend Components

| Component | Responsibility |
|-----------|---------------|
| `ChatWindow` | Conversation history, input box, WebSocket connection |
| `ToolCallCard` | Collapsible card showing tool call args and results (makes agent reasoning visible to user) |
| `ModelSelector` | Dropdown to switch LLM; persisted in localStorage |

## LLM Configuration

Multi-model routing via LiteLLM. Supported models at launch:

```python
SUPPORTED_MODELS = {
    "gpt-4o":                    {"provider": "openai"},
    "claude-opus-4-5":           {"provider": "anthropic"},
    "deepseek-chat":             {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner":         {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "minimax-text-01":           {"provider": "minimax",   "api_base": "https://api.minimax.chat/v1"},
    "ollama/llama3":             {"provider": "ollama",    "api_base": "http://localhost:11434"},
}
```

**Frontend toolchain:** React + TypeScript, scaffolded with Vite. Located in `frontend/`.

Required environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `NCBI_API_KEY` (optional).

**`docker-compose.yml` services:**
- `backend`: FastAPI app on port 8000
- `frontend`: Vite dev server on port 5173
- `ollama` (optional profile): local Ollama instance on port 11434 for offline LLM use

**Rate limiting and retries:** External API rate limiting and retry logic (backoff) are deferred to post-MVP. MVP tools propagate HTTP errors directly as `ToolResult(success=False, error=...)`.

## Out of Scope (MVP)

- Skill capture system
- Personalized user adaptation
- Literature-augmented validation (RAG + PubMed)
- Evolutionary workflow optimization
- pLM fine-tuning module
- Containerized tool deployment (ProteinBox full build)
