# ProteinClaw CLI/TUI Design Spec

**Date:** 2026-03-27
**Status:** Approved

## Background

ProteinClaw already has a basic CLI (`proteinclaw query <text>`) and a minimal Textual TUI in a single file (`proteinclaw/cli/app.py`). The goal of this work is to:

1. Make the package properly installable via `uv tool install proteinclaw` and `uv pip install proteinclaw`
2. Upgrade the TUI to a polished three-zone layout with modular Screen/Widget architecture
3. Add a first-run setup wizard for API key configuration

## Chosen Approach

**Modular TUI with screen/widget decomposition (Plan B).** The TUI is split into independent screens and widgets, each with a single responsibility and a clean interface. This makes the setup wizard a natural `SetupScreen`, the main chat a `MainScreen`, and tool call display a reusable `ToolCard` widget.

## Directory Structure

```
proteinclaw/
├── cli/
│   ├── __init__.py
│   ├── app.py              # main() entry point — routes to query or TUI
│   ├── renderer.py         # stdout renderer for query mode (unchanged)
│   └── tui/
│       ├── __init__.py
│       ├── app.py          # ProteinClawApp(App) — top-level Textual application
│       ├── screens/
│       │   ├── __init__.py
│       │   ├── setup.py    # SetupScreen — first-run API key configuration wizard
│       │   └── main.py     # MainScreen — three-zone conversation interface
│       └── widgets/
│           ├── __init__.py
│           ├── status_bar.py   # Top status bar (model name + agent state)
│           ├── conversation.py # Conversation area (streaming log + tool cards)
│           └── tool_card.py    # Inline tool call card widget
```

## Installation

### pyproject.toml Changes

- Move `textual>=0.50` from `[project.optional-dependencies] cli` into `[project.dependencies]`
- Add `[project.urls]` metadata (homepage, repository)
- Keep `[project.scripts]` entry: `proteinclaw = "proteinclaw.cli.app:main"`

### Install Commands

```bash
uv tool install proteinclaw        # global tool install
uv pip install proteinclaw         # virtualenv install
uv pip install proteinclaw[dev]    # with test dependencies
```

## TUI Layout

### SetupScreen (first-run wizard)

Shown when `needs_setup()` returns `True` (no usable API key found).

```
┌─ ProteinClaw Setup ──────────────────────────────┐
│                                                   │
│  Welcome to ProteinClaw!                          │
│  Let's configure your API keys.                   │
│                                                   │
│  Anthropic API Key:  [________________________]   │
│  OpenAI API Key:     [________________________]   │
│  DeepSeek API Key:   [________________________]   │
│  (other keys optional, press Enter to skip)       │
│                                                   │
│  Default model: [deepseek-chat]                   │
│                                                   │
│            [Save & Continue]                      │
└───────────────────────────────────────────────────┘
```

Behaviour:
- Pre-fills fields from existing environment variables if present
- Saves to `~/.config/proteinclaw/config.toml` on save
- Pushes `MainScreen` after saving

### MainScreen (three-zone layout)

```
┌─ ProteinClaw ─────────────── model: deepseek-chat ── ready ─┐
│                                                              │
│  > What is the structure of P04637?                         │
│                                                              │
│  ┌─ tool: uniprot ──────────────────────────────────────┐   │
│  │  args: {"id": "P04637"}                              │   │
│  │  result: TP53_HUMAN, tumor suppressor, 393 aa...     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  P04637 is TP53 (tumor protein p53)...                      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  Ask ProteinClaw... (/model /tools /clear /exit)            │
└──────────────────────────────────────────────────────────────┘
```

- **Top zone** — `StatusBar` widget: model name + agent state (`ready` / `thinking...` / `error`)
- **Middle zone** — `ConversationWidget`: streaming log with inline `ToolCard` widgets
- **Bottom zone** — `Input` widget (dock=bottom), placeholder shows available slash commands

### ToolCard Widget

Each tool call renders as a static inline card in the conversation area:

```
┌─ tool: uniprot ──────────────────┐
│  args: {"id": "P04637"}          │
│  result: TP53_HUMAN, 393 aa...   │
└──────────────────────────────────┘
```

Not collapsible in MVP. Result is added when `ObservationEvent` arrives.

## Configuration Management

### Config File

Path: `~/.config/proteinclaw/config.toml`

```toml
[keys]
anthropic_api_key = "sk-ant-..."
openai_api_key = ""
deepseek_api_key = "..."

[defaults]
model = "deepseek-chat"
```

### Priority

**Environment variables > config.toml > built-in defaults**

### New Functions in `proteinclaw/core/config.py`

```python
CONFIG_PATH = Path("~/.config/proteinclaw/config.toml").expanduser()

def load_user_config() -> None:
    """Read config.toml and inject into environment if env vars not already set."""

def save_user_config(keys: dict[str, str], default_model: str) -> None:
    """Write keys and default model to config.toml."""

def needs_setup() -> bool:
    """Return True if no usable API key is available from any source."""
```

## Data Flow

### Startup

```
main()
  └── _run_tui()
        └── ProteinClawApp.on_mount()
              ├── load_user_config()
              ├── needs_setup() == True  → push_screen(SetupScreen)
              └── needs_setup() == False → push_screen(MainScreen)
```

### Setup Flow

```
SetupScreen — user fills keys and clicks Save
  ├── save_user_config(keys, default_model)
  └── app.push_screen(MainScreen)
```

### Conversation Flow

```
MainScreen.on_input_submitted(query)
  └── async for event in run(query, history, model):
        ├── TokenEvent      → ConversationWidget.append_token(content)
        ├── ToolCallEvent   → ConversationWidget.add_tool_card(tool, args)
        ├── ObservationEvent→ current ToolCard.set_result(result)
        ├── DoneEvent       → StatusBar.set_state("ready")
        └── ErrorEvent      → StatusBar.set_state("error", message)
```

### StatusBar State Transitions

```
ready → thinking...   on first TokenEvent or ToolCallEvent
thinking... → ready   on DoneEvent
thinking... → error   on ErrorEvent (auto-resets to ready after 3 seconds)
```

## Slash Commands (unchanged)

| Command | Effect |
|---------|--------|
| `/model <name>` | Switch LLM model |
| `/tools` | List available tools |
| `/clear` | Clear conversation history and log |
| `/exit` | Quit application |

## Out of Scope

- Collapsible ToolCard (post-MVP)
- Model selector popup/panel (using `/model` command instead)
- `proteinclaw server` subcommand to start FastAPI separately
- Multi-session / tab support
