# ProteinClaw Ratatui CLI Design

**Date:** 2026-03-28
**Status:** Approved

## Background

The existing Python/Textual TUI (`proteinclaw/cli/tui/`) is replaced with a Rust binary using ratatui. The new CLI is a standalone binary (`proteinclaw-tui`) that starts the Python backend server on a local port, connects via WebSocket, and renders a terminal UI.

The Python core agent and server remain unchanged. The ratatui CLI is purely a new frontend that speaks the same WebSocket protocol as the React frontend.

## Architecture

### Communication Model

```
proteinclaw-tui (Rust/ratatui)
  ├── spawns: python -m uvicorn proteinclaw.server.main:app --port <free-port>
  ├── polls:  GET /health until 200 OK
  └── connects: WebSocket ws://127.0.0.1:<port>/ws/chat
        send: { "message": "...", "history": [...], "model": "..." }
        recv: { "type": "token"|"tool_call"|"observation"|"done"|"error", ... }
```

The Python server is killed via `Drop` on `ServerHandle` when the CLI exits.

### Runtime Model: State Machine + Async Channel (Plan A+C)

```
tokio runtime
  ├── main task: terminal render loop (sync draw + select! on events)
  ├── spawn_blocking: crossterm event reader → AppEvent::Key
  └── tokio task: ws reader → AgentEvent → AppEvent::WsMessage → event_tx

app.update(event) — pure sync, modifies AppState only
app.draw(frame)   — pure sync, renders from AppState
```

All I/O is async and off the render thread. State changes are synchronous and deterministic.

## Directory Structure

```
ProteinClaw/
├── Cargo.toml              # workspace root (new)
│     members = ["cli-tui"]
├── cli-tui/
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs         # entry: start server, init terminal, run event loop
│       ├── app.rs          # App struct, AppState enum, update(), draw()
│       ├── server.rs       # ServerHandle: spawn python, poll_health, Drop kill
│       ├── ws.rs           # WebSocket client task, deserialize frames → AppEvent
│       ├── events.rs       # AppEvent enum + AgentEvent enum
│       ├── config.rs       # read/write ~/.config/proteinclaw/config.toml
│       └── views/
│           ├── mod.rs
│           ├── setup.rs    # SetupView: three-step wizard
│           └── main.rs     # MainView: status bar + conversation + input
└── src-tauri/              # unchanged, remains independent (not in workspace)
```

`src-tauri/` is kept outside the Cargo workspace to avoid conflicts with Tauri's build system.

## Dependencies (cli-tui/Cargo.toml)

| Crate | Purpose |
|-------|---------|
| `ratatui` | TUI rendering |
| `crossterm` | terminal backend |
| `tokio` (features = ["full"]) | async runtime |
| `tokio-tungstenite` | WebSocket client |
| `serde` / `serde_json` | WS message serialization |
| `toml` | config.toml read/write |

## Event Types

```rust
enum AppEvent {
    Key(KeyEvent),
    Resize(u16, u16),
    WsMessage(AgentEvent),
    WsError(String),
    ServerReady,
    ServerFailed(String),
    Tick,                    // periodic tick for cursor blink
}

enum AgentEvent {
    Thinking(String),
    Token(String),
    ToolCall { tool: String, args: serde_json::Value },
    Observation { result: serde_json::Value },
    Done,
    Error(String),
}
```

## AppState

```rust
enum AppState {
    Setup(SetupState),
    Main(MainState),
}
```

Startup: `load_config()` → `needs_setup()` → push `Setup` or `Main`.

## SetupView

Three-step wizard, identical flow to the Python SetupScreen.

```rust
enum SetupStep { ChooseProvider, EnterApiKey, ChooseModel }

struct SetupState {
    step: SetupStep,
    providers: Vec<Provider>,    // (id, display_name, env_key)
    selected_provider: usize,
    api_key_input: String,
    api_key_visible: bool,       // always false (password mode)
    models: Vec<String>,
    selected_model: usize,
}
```

### Layout (centered card, same every step)

```
┌─────────────────────────────────────────────────────────┐
│                     ProteinClaw                         │
│           Set up your default model to get started.     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Choose a provider                                │  │
│  │  ─────────────────────────────────────────────   │  │
│  │    Anthropic                                      │  │
│  │  ▶ OpenAI                                         │  │
│  │    DeepSeek                                       │  │
│  │    MiniMax                                        │  │
│  │    Ollama (local, no API key needed)              │  │
│  │                                                   │  │
│  │  Provider decides which API key appears next.     │  │
│  └───────────────────────────────────────────────────┘  │
│  ↑↓ navigate   Enter select                             │
└─────────────────────────────────────────────────────────┘
```

### Key Bindings

| Step | Key | Action |
|------|-----|--------|
| ChooseProvider | `↑` `↓` | move cursor |
| ChooseProvider | `Enter` | select → EnterApiKey (Ollama skips to ChooseModel) |
| EnterApiKey | chars | append to input |
| EnterApiKey | `Backspace` | delete last char |
| EnterApiKey | `Enter` | save key → ChooseModel |
| EnterApiKey | `Esc` | skip (empty key) → ChooseModel |
| ChooseModel | `↑` `↓` | move cursor |
| ChooseModel | `Enter` | save config, transition to `AppState::Main` |

## MainView

### Layout

```
┌─ ProteinClaw ──────────────── model: deepseek-chat ── ready ─┐
│                                                               │
│  > What is the structure of P04637?                          │
│                                                               │
│  ╔═ tool: uniprot ══════════════════════════════════════╗    │
│  ║  args: {"id": "P04637"}                              ║    │
│  ║  result: TP53_HUMAN, tumor suppressor, 393 aa...     ║    │
│  ╚══════════════════════════════════════════════════════╝    │
│                                                               │
│  P04637 is TP53 (tumor protein p53)...                       │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│  Ask ProteinClaw... (/model /tools /clear /exit)  _          │
└───────────────────────────────────────────────────────────────┘
```

- **Top bar**: `Paragraph`, left = title, right = `model: X — state`
- **Conversation**: scrollable `Paragraph`, `ToolCall` messages rendered with `Block` border
- **Input**: `Paragraph` docked bottom, shows input text + cursor position

```rust
struct MainState {
    model: String,
    agent_state: AgentState,        // Ready | Thinking | Error(String)
    messages: Vec<Message>,
    input: String,
    input_cursor: usize,
    scroll_offset: u16,
    ws_tx: Sender<String>,          // send queries to WS writer task
    history: Vec<HistoryEntry>,     // { role, content } for WS payload
}

enum AgentState { Ready, Thinking, Error(String) }

enum Message {
    User(String),
    Thinking(String),
    AssistantToken(String),         // accumulated in place: on Token event, append to the last AssistantToken or push a new one
    ToolCall { tool: String, args: Value, result: Option<Value> },
    SystemInfo(String),             // slash command feedback
    Error(String),
}
```

### Key Bindings

| Key | Action |
|-----|--------|
| chars | append to input |
| `Backspace` | delete char at cursor |
| `←` `→` | move input cursor |
| `Enter` | submit query or slash command |
| `↑` `↓` | scroll conversation |
| `Ctrl+C` / `Esc` | quit |

### Slash Commands

| Command | Effect |
|---------|--------|
| `/model <name>` | switch model, update status bar |
| `/tools` | list available tools (via GET /tools) |
| `/clear` | clear messages and history |
| `/exit` | quit |

## Server Lifecycle (server.rs)

```rust
pub struct ServerHandle { child: Child, pub port: u16 }

pub async fn start() -> Result<ServerHandle> {
    let port = find_free_port(8000);
    let child = Command::new("python")
        .args(["-m", "uvicorn", "proteinclaw.server.main:app",
               "--host", "127.0.0.1", "--port", &port.to_string()])
        .stdout(Stdio::null()).stderr(Stdio::null())
        .spawn()?;
    poll_health(port, 30).await?;   // GET /health every 1s, timeout 30s
    Ok(ServerHandle { child, port })
}

impl Drop for ServerHandle {
    fn drop(&mut self) { let _ = self.child.kill(); }
}
```

`find_free_port` tries ports from 8000 upward with `TcpListener::bind`.

## Config (config.rs)

Reads and writes the same `~/.config/proteinclaw/config.toml` as the Python layer:

```toml
[keys]
ANTHROPIC_API_KEY = "sk-ant-..."
DEEPSEEK_API_KEY = ""

[defaults]
model = "deepseek-chat"
```

```rust
pub struct Config {
    pub keys: HashMap<String, String>,
    pub default_model: String,
}

pub fn load() -> Config { ... }
pub fn save(config: &Config) -> Result<()> { ... }
pub fn needs_setup(config: &Config) -> bool { ... }
```

`needs_setup` mirrors Python logic: check that the env key for `default_model`'s provider is non-empty. Ollama always returns false.

## Deletion Scope

The following Python files are deleted as part of this work:

- `proteinclaw/cli/tui/` (entire directory)
- `proteinclaw/cli/app.py` (entry point — replaced by `proteinclaw-tui` binary)
- `proteinclaw/cli/renderer.py` (stdout renderer — no longer needed)
- `tests/proteinclaw/tui/` (entire directory)

The `proteinclaw` Python package entry point (`proteinclaw.cli.app:main`) is removed from `pyproject.toml`. The CLI binary is now the Rust binary `proteinclaw-tui`.

## Out of Scope

- Collapsible ToolCard
- Mouse support
- `/tools` output fetched via HTTP GET (can be added post-MVP; for MVP show static list from config)
- Windows/macOS packaging of the CLI binary (separate from Tauri desktop app)
- Syntax highlighting in conversation area
