# ProteinClaw TUI: React/Ink Rewrite Design

**Date:** 2026-03-31
**Status:** Approved
**Branch:** feature/ratatui-cli

---

## Overview

Replace the existing Rust/ratatui CLI TUI (`cli-tui/`) with a React/Ink terminal UI running on the Bun runtime. The new TUI is a faithful port of Claude Code's architecture — including its custom React-to-terminal rendering engine — adapted to connect to ProteinClaw's existing Python backend via WebSocket.

The Python backend is unchanged. Only the frontend (terminal UI process) is replaced.

---

## Architecture

### Directory Structure

```
ProteinClaw/
├── tui/                            ← new (replaces cli-tui/)
│   ├── src/
│   │   ├── ink/                    ← Claude Code custom renderer (copied verbatim)
│   │   │   ├── components/         ←   Box, Text, ScrollBox, App, etc.
│   │   │   ├── termio/             ←   ANSI/CSI/SGR/OSC parsing
│   │   │   ├── reconciler.ts       ←   React Fiber custom renderer
│   │   │   ├── render-node-to-output.ts
│   │   │   ├── ink.tsx             ←   Core Ink class
│   │   │   └── index.tsx           ←   Public API + theme wrapper
│   │   ├── screens/
│   │   │   ├── REPL.tsx            ←   Main chat interface (adapted)
│   │   │   ├── Doctor.tsx          ←   Diagnostics (adapted)
│   │   │   └── Setup.tsx           ←   First-run setup wizard
│   │   ├── state/
│   │   │   ├── AppStateStore.ts    ←   Slice-based store (adapted from Claude Code)
│   │   │   └── selectors.ts
│   │   ├── context/
│   │   │   ├── modalContext.tsx
│   │   │   ├── notifications.tsx
│   │   │   └── overlayContext.tsx
│   │   ├── hooks/                  ←   Cleaned subset of Claude Code hooks
│   │   ├── components/             ←   Shared UI components
│   │   ├── services/
│   │   │   ├── ws.ts               ←   WebSocket client (new, ProteinClaw protocol)
│   │   │   └── config.ts           ←   Config read/write (~/.config/proteinclaw/)
│   │   ├── main.tsx                ←   Entry point
│   │   └── cli.tsx                 ←   CLI argument parsing
│   ├── package.json
│   ├── tsconfig.json
│   └── bunfig.toml
└── cli-tui/                        ← deleted
```

### Modules Copied from Claude Code

| Module | Action |
|--------|--------|
| `src/ink/` | Copy verbatim — custom React→terminal renderer |
| `src/screens/REPL.tsx` | Copy and adapt — replace Anthropic API with WebSocket |
| `src/screens/Doctor.tsx` | Copy and adapt — replace Anthropic checks with ProteinClaw checks |
| `src/state/AppStateStore.ts` | Copy and adapt — trim Anthropic fields, add ProteinClaw fields |
| `src/context/` (modal, notifications, overlay) | Copy verbatim |
| `src/hooks/` (input, scroll, timing, keyboard) | Copy subset, remove OAuth/MCP/LSP hooks |
| `src/components/` | Copy verbatim |

### Modules Removed (Anthropic-specific, not needed)

| Module | Reason |
|--------|--------|
| `services/oauth/` | Auth via config file instead |
| `services/analytics/` | No telemetry |
| `services/mcp/` | No Model Context Protocol |
| `services/voice.ts` | No voice input |
| `services/lsp/` | No IDE Language Server |
| `coordinator/` | No multi-agent |
| `bridge/` | No IDE integration |
| `plugins/` | No plugin marketplace |
| `services/remoteManagedSettings/` | No remote config |

---

## Data Flow

### Process Startup

```
bun run tui/src/main.tsx
    │
    ├─ Parse CLI args (cli.tsx)
    ├─ Load config (~/.config/proteinclaw/config.toml)
    ├─ If not configured → render <Setup> screen
    ├─ spawn Python server (proteinclaw/server/main.py)
    ├─ Poll /health until ready
    ├─ Connect WebSocket ws://127.0.0.1:{port}/ws/chat
    └─ render(<App>) → show <REPL> screen
```

### WebSocket Protocol (existing, unchanged)

**Outgoing (TUI → Python):**
```json
{
  "message": "string",
  "history": [{"role": "user|assistant", "content": "string"}],
  "model": "string"
}
```

**Incoming (Python → TUI):**
```json
{ "type": "thinking",   "content": "..." }
{ "type": "token",      "content": "..." }
{ "type": "tool_call",  "tool": "...", "args": {...} }
{ "type": "observation","result": {...} }
{ "type": "done" }
{ "type": "error",      "message": "..." }
```

### Event → UI Mapping

| WS Event | Claude Code REPL concept | Rendered as |
|----------|--------------------------|-------------|
| `token` | Streaming assistant message | `<AssistantMessage>` (streaming) |
| `thinking` | Thinking block | `<ThinkingBlock>` (collapsible) |
| `tool_call` + `observation` | Tool use card | `<ToolCallCard>` (expandable) |
| `done` | Turn complete | Stop spinner, re-enable input |
| `error` | Error message | `<ErrorMessage>` red text |

---

## State Management

```typescript
type ProteinClawAppState = {
  // Navigation
  view: 'repl' | 'setup' | 'doctor'

  // Conversation
  messages: Message[]
  history: HistoryEntry[]
  model: string
  isThinking: boolean

  // Connection
  wsStatus: 'connecting' | 'connected' | 'error'
  serverPort: number | null
}
```

Pattern: slice-based subscriptions via `useSyncExternalStore`, same as Claude Code's `AppStateStore`.

---

## Component Structure

### REPL Screen

```
<App>                             Ink root — manages raw mode, resize events
  <ModalContext.Provider>
  <NotificationsContext.Provider>
    <REPL>
      <StatusBar>                 model name · wsStatus · thinking indicator
      <VirtualMessageList>        virtual scroll — renders only visible messages
        <UserMessage>
        <AssistantMessage>        streaming tokens
        <ThinkingBlock>           collapsible
        <ToolCallCard>            tool_call + observation merged
      <PromptInput>               multiline, history, vim-mode, slash commands
```

### Setup Screen

```
<Setup>
  ASCII logo + welcome text
  <TextInput>   API key (masked)
  <Select>      default model
  → save to config.toml → transition to REPL
```

### Doctor Screen

```
<Doctor>
  Python server status (HTTP /health)
  WebSocket connectivity
  API key presence check
  Dependency versions
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Shift+Enter` | Insert newline |
| `↑ / ↓` | Navigate input history |
| `Ctrl+C` | Cancel current request / exit |
| `Ctrl+L` | Clear screen |
| `Ctrl+O` | Toggle prompt ↔ transcript view |
| `Esc` | Cancel input |
| `/clear` | Clear conversation |
| `/model <name>` | Switch model |
| `/tools` | List available tools |
| `/exit` | Quit |
| `/doctor` | Open Doctor screen |

---

## Error Handling

- **WebSocket disconnect:** StatusBar turns red, auto-reconnect with exponential backoff (1s, 2s, 4s, max 30s)
- **Python server crash:** ErrorOverlay shown, prompt user to run `/doctor`
- **Render panic / unhandled exception:** Restore terminal raw mode before exit (same guarantee as current Rust panic hook)
- **Config missing:** Redirect to Setup screen instead of crashing

---

## Build & Run

```toml
# bunfig.toml
[install]
exact = true
```

```json
// package.json scripts
{
  "start": "bun run src/main.tsx",
  "dev":   "bun --watch run src/main.tsx",
  "build": "bun build src/main.tsx --outfile dist/proteinclaw-tui",
  "test":  "bun test"
}
```

**Runtime requirement:** Bun >= 1.1
**TypeScript target:** ES2022
**React version:** 18 (same as Claude Code)
**Ink version:** custom (copied from Claude Code source)

---

## Migration

1. Delete `cli-tui/` after `tui/` passes smoke tests
2. Update `scripts/dev.sh` and `scripts/tui.ps1` to point to `bun run tui/src/main.tsx`
3. Update root `Cargo.toml` workspace to remove `cli-tui` member
