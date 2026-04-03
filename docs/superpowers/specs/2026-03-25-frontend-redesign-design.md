# Frontend Redesign — Claude-style UI

**Date:** 2026-03-25
**Status:** Approved

## Goal

Redesign the ProteinClaw frontend to match the aesthetic and UX of the Claude app: sidebar with conversation history, clean centered chat area, Markdown rendering, and a fixed auto-growing input textarea.

## Decisions

| Topic | Decision |
|-------|----------|
| Layout | Left sidebar + right chat area |
| Conversation storage | LocalStorage (pure frontend, no backend changes) |
| Markdown rendering | `react-markdown` |
| Theme | Light (existing CSS variables — `--accent: #aa3bff`) |
| Implementation | Full component rewrite — inline styles → CSS classes |

## Architecture

### Component Tree

```
App
├── Sidebar
│   ├── NewProjectButton
│   └── ProjectList
│       └── ProjectItem (accordion, expand/collapse)
│           ├── NewChatButton
│           └── ConversationList (chat items inside project)
└── ChatWindow
    ├── TopBar (conversation title + ModelSelector)
    ├── MessageList  ← scrollable, overflow-y: auto
    │   └── MessageBubble (user bubble / assistant text)
    │       └── ToolCallCard (collapsible tool call + result)
    └── InputArea  ← fixed, flex-shrink: 0
```

### New Files

| File | Purpose |
|------|---------|
| `src/components/Sidebar.tsx` | Sidebar shell + New Project button + ProjectList |
| `src/components/ProjectItem.tsx` | Accordion item: project header (expand/collapse) + chat list + New Chat button |
| `src/hooks/useProjects.ts` | CRUD for projects and conversations, LocalStorage sync |
| `src/lib/storage.ts` | Raw LocalStorage read/write helpers |

### Changed Files

| File | Change |
|------|--------|
| `src/App.tsx` | Add conversation state, wire Sidebar ↔ ChatWindow |
| `src/components/ChatWindow.tsx` | Split into TopBar + MessageList + InputArea; inline styles → CSS classes |
| `src/components/MessageBubble.tsx` | New component replacing inline message rendering; adds `react-markdown` |
| `src/components/ToolCallCard.tsx` | Style upgrade to match new theme |
| `src/index.css` | Add component CSS classes (`.sidebar`, `.chat-window`, `.message-bubble`, etc.) |

## Data Model

Stored in `localStorage` under key `proteinclaw_projects`:

```ts
interface Project {
  id: string;           // crypto.randomUUID()
  name: string;         // user-defined project name
  createdAt: number;    // Unix timestamp ms
  conversations: Conversation[];
}

interface Conversation {
  id: string;           // crypto.randomUUID()
  title: string;        // First user message, truncated to 60 chars
  model: string;        // e.g. "deepseek-chat"
  createdAt: number;    // Unix timestamp ms
  messages: Message[];
}

interface Message {
  role: "user" | "assistant";
  content: string;
  toolCalls?: WsEvent[];  // existing type, unchanged
}
```

`useProjects` exposes:
- `projects: Project[]` — sorted newest first
- `activeProjectId: string | null`
- `activeConversationId: string | null`
- `createProject(name) → id`
- `createConversation(projectId, model) → id`
- `selectConversation(projectId, conversationId)`
- `appendMessage(conversationId, message)` — called by `useChat` on each WS event

## Scroll Behaviour

- **MessageList**: `flex: 1; overflow-y: auto` — fills remaining height, scrollable
- On new message arrival: auto-scroll to bottom **unless** the user has scrolled up — detected by checking `scrollTop + clientHeight < scrollHeight - 50px`
- **InputArea**: `flex-shrink: 0` — always pinned to the bottom of ChatWindow, never scrolls away

## Input Area

- `<textarea>` replacing the current `<input>`
- Auto-grows with content: starts at 1 row, max-height 150px, then scrolls internally
- Submit on Enter; Shift+Enter inserts newline
- Disabled + visual spinner while waiting for WS response

## Markdown Rendering

- Add `react-markdown` dependency
- Render assistant `content` through `<ReactMarkdown>`
- User messages remain plain text (no markdown rendering needed)
- Code blocks: styled with existing `--code-bg` and `--mono` CSS variables — no extra syntax highlight library

## Sidebar

- Fixed width: 240px
- **"New Project" button** at top → prompts for project name (inline input), calls `createProject`
- **Project list** (accordion style):
  - Each `ProjectItem` shows project name + chat count; click header to expand/collapse
  - Expanded state: shows "＋ New Chat" button + list of conversations in that project
  - "New Chat" → calls `createConversation(projectId, model)`, auto-selects new chat
  - Active conversation highlighted with `--accent-bg` left border
  - Each conversation item shows title (truncated to 40 chars) + relative date
- Newly created project is auto-expanded
- No rename/delete UI in v1 (keep scope minimal)

## What Is Not Changing

- WebSocket chat logic (`useChat.ts`) — signature changes from `useChat()` to `useChat(conversationId: string, onMessage: (msg: Message) => void)`; internal WS logic unchanged
- Backend Python code — zero changes
- `ModelSelector` — reused as-is, moved into TopBar
- `useStoredModel` — reused as-is
- All existing types in `types.ts` — unchanged

## Dependencies to Add

```
react-markdown
```

One new `npm` dependency. No other new packages.
