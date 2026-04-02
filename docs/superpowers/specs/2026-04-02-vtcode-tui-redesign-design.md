# TUI Redesign — vtcode-style Layout

**Date:** 2026-04-02  
**Scope:** `cli-tui/` crate only  
**Reference:** https://github.com/vinhnx/vtcode

## Overview

Redesign the ProteinClaw terminal UI from a single flat `ui.rs` into a widget-based architecture that matches vtcode's visual design: Header / Transcript / Input / Footer four-layer layout, three adaptive layout modes, a tool-call sidebar in Wide mode, and a `/`-triggered command popup.

The backend connection (WebSocket to Python server) is unchanged.

---

## Architecture

### File Structure

```
cli-tui/src/
├── main.rs
├── app.rs          ← extend with token_counts, current_dir, command_popup state
├── config.rs
├── events.rs
├── server.rs
├── ws.rs
├── ui.rs           ← layout orchestration only (detect layout mode, dispatch to widgets)
└── widgets/
    ├── mod.rs
    ├── header.rs
    ├── footer.rs
    ├── transcript.rs
    ├── input.rs
    ├── sidebar.rs
    └── command_popup.rs
```

### Widget responsibilities

| Widget | Responsibility |
|---|---|
| `header.rs` | Render top bar: brand · version · dir · model · connection · tokens |
| `footer.rs` | Render bottom bar: status · context hints · model · spinner |
| `transcript.rs` | Render chat messages (migrated from current `ui.rs`) |
| `input.rs` | Render input box with accent border when active |
| `sidebar.rs` | Render tool call log panel (Wide mode only) |
| `command_popup.rs` | Render floating `/` command menu above input |
| `ui.rs` | Detect layout mode, compute `Rect` splits, call widgets |

---

## Layout Modes

Detected from `frame.area().width` on every render:

| Mode | Width | Differences |
|---|---|---|
| Compact | < 80 cols | No borders; Header shows name + status only; Footer single line minimal |
| Standard | 80–119 cols | All four layers with titled `Block` borders |
| Wide | ≥ 120 cols | Standard + right sidebar (~30% width) for Tool Calls |

---

## Widget Designs

### Header

```
ProteinClaw v0.2  │  ~/projects/my-research  │  claude-sonnet-4        ● connected │ ↑1.2k ↓450 tok
```

- **Left:** `ProteinClaw` (accent color `#00b0aa`) + version (dimmed) + `│` + current working dir (dimmed) + `│` + model name
- **Right:** connection status dot + label (color: green/yellow/red) + `│` + `↑{in} ↓{out} tok`
- Height: 1 row; background: slightly lighter than terminal bg (`Color::DarkGray` or equivalent)
- Compact: omit dir and token counts; show `ProteinClaw` + status dot only

### Footer

Three hint states based on `App` mode:

| App state | Center hints |
|---|---|
| Idle (no pending message) | `? help • / command` |
| Processing (assistant streaming) | `ctrl+c stop` |
| Editing (textarea focused, non-empty) | `Enter 发送 • ↑ 历史 • Esc 取消` |

Layout:
- **Left:** connection status (same color as header)
- **Center:** context hints (dimmed)
- **Right:** model name (dimmed)
- When processing: spinner character cycles `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` inserted between left and center
- Height: 1 row (Compact) or 2 rows (Standard/Wide: row 1 = status, row 2 = hints)

### Transcript

- Migrated from current `ui.rs` `draw_messages()` with no behavioral changes
- Wrapped in a `Block` with title `"Transcript"` in Standard/Wide modes
- Border is always dimmed (`Color::DarkGray`) — Transcript is read-only, never focused
- Scroll behavior unchanged

### Input

- Wraps existing `tui-textarea` widget
- Border is always accent color (`#00b0aa`) + bold — Input is the single permanent focus area
- Height: dynamic (clamp 3–8 rows, same as current)

### Sidebar (Wide only)

- Title: `"Tool Calls"`
- Lists every `AssistantPart::ToolCall` from all messages in order:
  - `⏺ tool_name` (green = done, yellow = running)
  - Indented: truncated args and result summary (1 line each)
- Fixed width: `area.width * 30 / 100`, minimum 24 cols
- Non-interactive (read-only log)

### Command Popup

Triggered when the input textarea's first character is `/`.

- Floats above the input box, same horizontal span
- Accent-color border, title: `"Commands"`
- Command list (always shown in full, filtered as user types more):

| Command | Description |
|---|---|
| `/model <name>` | 切换模型 |
| `/clear` | 清空会话历史 |
| `/system <text>` | 设置 system prompt |
| `/help` | 显示全部命令 |
| `/export` | 导出会话为 JSON（写入当前目录 `proteinclaw-session-{timestamp}.json`） |

- `↑`/`↓`: navigate selection
- `Enter`: fill selected command into input (do not send)
- `Esc`: dismiss popup, leave input text unchanged
- Typing more characters: real-time filter by prefix match
- Height: number of filtered items + 2 (borders), max 8

---

## App State Extensions

```rust
// app.rs additions
pub struct App {
    // ... existing fields ...
    pub token_counts: (u32, u32),        // (input_tokens, output_tokens)
    pub current_dir: String,             // populated at startup from std::env::current_dir()
    pub command_popup: Option<CommandPopupState>,
    pub footer_mode: FooterMode,         // Idle | Processing | Editing
}

pub struct CommandPopupState {
    pub filter: String,           // text after '/' used to filter
    pub selected: usize,          // currently highlighted row
}

pub enum FooterMode {
    Idle,
    Processing,
    Editing,
}
```

Token counts are updated by a new `WsEvent::TokenUsage { input: u32, output: u32 }` event if the backend sends it, otherwise incremented heuristically from streamed tokens.

---

## Data Flow

```
main.rs → App::new() → reads current_dir, version from Cargo.toml const
WsEvent::Done → update token_counts if usage data present
Key '/' in input → set command_popup = Some(CommandPopupState::default())
Key Esc / Enter in popup → clear command_popup
textarea content changes → update footer_mode (Editing if non-empty)
streaming active → footer_mode = Processing
```

---

## Error Handling

- If `current_dir()` fails: display `"~"` as fallback
- Token counts missing from backend: show `↑? ↓?` until first update
- Terminal narrower than expected for Compact mode: truncate strings with `…`

---

## Testing

- No new test infrastructure needed; verify visually by running `cargo run` in `cli-tui/`
- Resize terminal to verify layout mode transitions at 80 and 120 cols
- Type `/` to verify popup appears; type more chars to verify filtering; `↑↓Enter` to verify selection
