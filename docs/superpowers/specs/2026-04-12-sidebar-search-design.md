# Sidebar Search Design

**Date:** 2026-04-12
**Status:** Approved

## Overview

Add search functionality to the sidebar's Search button. Clicking it opens a floating panel to the right of the sidebar that filters all conversation titles in real time. Selecting a result navigates to that conversation and closes the panel.

---

## Component & State

All state lives in `Sidebar.tsx` — no new files, no prop drilling.

**New state:**
- `showSearch: boolean` — panel open/close
- `searchQuery: string` — controlled input value

**Search logic (pure frontend filter):**
```ts
const searchResults = projects
  .flatMap((p) => p.conversations.map((c) => ({ ...c, projectId: p.id })))
  .filter((c) => c.title.toLowerCase().includes(searchQuery.toLowerCase()))
  .sort((a, b) => b.createdAt - a.createdAt);
```

**Interactions:**
- Click Search button → `setShowSearch(true)`, input auto-focuses
- Escape key / click overlay → close panel, clear query
- Click result → `onSelectConversation(projectId, convId)` + close panel + clear query

---

## UI Layout & Positioning

```
┌──────────────┐ ┌─────────────────────────────┐
│   Sidebar    │ │  🔍 Search chats...      [X] │
│              │ ├─────────────────────────────┤
│  [+ New]     │ │ Title A                Today │
│  [Search] ←──┘ │ Title B                  1d  │
│  [Plugins]   │ │ Title C                  2d  │
│              │ │ ...                          │
└──────────────┘ └─────────────────────────────┘
```

**Panel positioning:**
- `position: fixed`
- `left: 220px` (matches sidebar width)
- `top: 0`, `height: 100vh`
- `width: 300px`
- `z-index: 500` (below feedback modal at 1000)
- Background: `var(--surface)`, `border-right: 1px solid var(--border)`

**Panel structure:**
- Header: Search icon + `<input>` + X close button
- Results list: scrollable, each row shows `conv.title` + `relativeTime(conv.createdAt)`
- Empty state: "No chats found" when query has no matches
- Transparent overlay (`z-index: 499`) behind panel to catch outside clicks

---

## CSS Classes

All new classes added to `frontend/src/index.css`, using existing design tokens only.

| Class | Purpose |
|---|---|
| `.search-overlay` | Full-screen transparent backdrop, `position: fixed, inset: 0, z-index: 499` |
| `.search-panel` | Fixed panel, `left: 220px, top: 0, width: 300px, height: 100vh, z-index: 500` |
| `.search-panel__input-wrap` | Flex row containing search icon, input, and X button; `border-bottom: 1px solid var(--border-light)` |
| `.search-panel__input` | Full-width text input, no border, transparent background |
| `.search-panel__clear` | X button, same style as `right-sidebar__close` |
| `.search-panel__list` | `flex: 1, overflow-y: auto` results container |
| `.search-panel__item` | Flex row result, hover → `var(--border)` background, `cursor: pointer` |
| `.search-panel__item-title` | Truncated title text, `flex: 1` |
| `.search-panel__item-time` | Right-aligned relative time, `var(--text-xs)` |
| `.search-panel__empty` | "No chats found" centered muted text |

---

## Files Changed

| File | Change |
|---|---|
| `frontend/src/components/Sidebar.tsx` | Add `showSearch` + `searchQuery` state; wire Search button; add panel + overlay JSX |
| `frontend/src/index.css` | Add `.search-panel` and related classes |
