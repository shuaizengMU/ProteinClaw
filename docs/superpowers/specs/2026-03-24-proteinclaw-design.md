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
├── proteinclaw/              # FastAPI backend
│   ├── agent/
│   │   ├── loop.py           # ReAct agent main loop
│   │   ├── llm.py            # LiteLLM wrapper, multi-model routing
│   │   └── prompt.py         # System prompt templates
│   ├── tools/
│   │   ├── registry.py       # Tool base class + auto-discovery
│   │   ├── uniprot.py        # UniProt query tool (MVP)
│   │   └── blast.py          # BLAST tool (MVP)
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
                                 Tool Registry → External APIs (UniProt, NCBI)
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

## Tool Layer

### Tool Base Class

```python
class ProteinTool(BaseModel):
    name: str
    description: str       # Injected into system prompt so LLM knows when to use it
    parameters: dict       # JSON Schema for LLM argument generation

    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError
```

New tools are registered via `@register_tool` decorator and auto-discovered at startup. No additional configuration required.

### MVP Tools

| Tool | Input | API | Output |
|------|-------|-----|--------|
| `UniProtTool` | UniProt Accession ID (e.g. `P04637`) | `https://rest.uniprot.org/uniprotkb/{id}.json` | Name, function, GO terms, sequence length, species |
| `BLASTTool` | Protein sequence (FASTA) | NCBI BLAST E-utilities (async submit → poll) | Top-N hits with E-value and coverage |

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

### WebSocket Event Types

```json
{"type": "thinking",    "content": "I need to look up..."}
{"type": "tool_call",   "tool": "uniprot", "args": {"id": "P04637"}}
{"type": "observation", "tool": "uniprot", "result": {...}}
{"type": "token",       "content": "该蛋白是..."}
{"type": "done"}
{"type": "error",       "message": "..."}
```

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
    "gpt-4o":              {"provider": "openai"},
    "claude-opus-4-6":     {"provider": "anthropic"},
    "deepseek-chat":       {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner":   {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "minimax-text-01":     {"provider": "minimax",   "api_base": "https://api.minimax.chat/v1"},
    "ollama/llama3":       {"provider": "ollama",    "api_base": "http://localhost:11434"},
}
```

Required environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `NCBI_API_KEY` (optional).

## Out of Scope (MVP)

- Skill capture system
- Personalized user adaptation
- Literature-augmented validation (RAG + PubMed)
- Evolutionary workflow optimization
- pLM fine-tuning module
- Containerized tool deployment (ProteinBox full build)
