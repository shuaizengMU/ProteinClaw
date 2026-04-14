# Sidebar Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the sidebar Search button to open a fixed floating panel that filters conversation titles in real time.

**Architecture:** All state (`showSearch`, `searchQuery`) lives in `Sidebar.tsx`. A `position: fixed` panel and transparent overlay are rendered inside the `<aside>` element — `fixed` positioning means they escape the sidebar's bounds. Search is a pure frontend filter over `projects[].conversations[].title`. No new component files needed.

**Tech Stack:** React + TypeScript, existing CSS design tokens, lucide-react icons.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `frontend/src/index.css` | Add `.search-overlay` + `.search-panel` CSS classes |
| Modify | `frontend/src/components/Sidebar.tsx` | Add search state, wire button, render overlay + panel |

---

## Task 1: CSS — search panel styles

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Append search panel CSS to `frontend/src/index.css`**

Add the following block at the very end of the file:

```css
/* ── Search Panel ────────────────────────────────────────── */
.search-overlay {
  position: fixed;
  inset: 0;
  z-index: 499;
}

.search-panel {
  position: fixed;
  left: 220px;
  top: 0;
  width: 300px;
  height: 100vh;
  background: var(--surface);
  border-right: 1px solid var(--border);
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.08);
  z-index: 500;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-panel__input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.search-panel__icon {
  color: var(--text-xs);
  flex-shrink: 0;
}

.search-panel__input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  font-family: var(--sans);
  color: var(--text-h);
  min-width: 0;
}

.search-panel__input::placeholder {
  color: var(--text-xs);
}

.search-panel__clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text);
  flex-shrink: 0;
  transition: background 120ms, color 120ms;
}

.search-panel__clear:hover {
  background: var(--border);
  color: var(--text-h);
}

.search-panel__list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

.search-panel__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  cursor: pointer;
  transition: background 120ms;
}

.search-panel__item:hover {
  background: var(--border);
}

.search-panel__item-title {
  flex: 1;
  font-size: 14px;
  font-family: var(--sans);
  color: var(--text-h);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-panel__item-time {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-xs);
}

.search-panel__empty {
  padding: 24px 14px;
  font-size: 14px;
  color: var(--text-xs);
  text-align: center;
}
```

- [ ] **Step 2: Verify no CSS errors**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw/frontend
npx vite build --mode development 2>&1 | grep -i "error" | grep -i "css" | head -10
```

Expected: no output (no CSS errors).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: add search panel CSS"
```

---

## Task 2: Sidebar — search state and panel JSX

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Add `X` to lucide imports**

The current import block starts at line 1. Change:
```tsx
import {
  Plus,
  Search,
  Puzzle,
  Settings,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  ListFilter,
  FolderPlus,
  FolderOpen,
  MoreVertical,
  Folder,
  PencilLine,
  Trash2,
  Sun,
  Moon,
  Laptop,
  Palette,
  Key,
  Pin,
  PinOff,
} from "lucide-react";
```
To:
```tsx
import {
  Plus,
  Search,
  Puzzle,
  Settings,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  ListFilter,
  FolderPlus,
  FolderOpen,
  MoreVertical,
  Folder,
  PencilLine,
  Trash2,
  Sun,
  Moon,
  Laptop,
  Palette,
  Key,
  Pin,
  PinOff,
  X,
} from "lucide-react";
```

- [ ] **Step 2: Add `showSearch` and `searchQuery` state + `searchInputRef`**

Inside the `Sidebar` function body, after the existing `const renameInputRef = useRef<HTMLInputElement>(null);` line, add:

```tsx
const searchInputRef = useRef<HTMLInputElement>(null);
const [showSearch, setShowSearch] = useState(false);
const [searchQuery, setSearchQuery] = useState("");
```

- [ ] **Step 3: Add `closeSearch` helper**

After the existing `function handleCollapseAll()` function, add:

```tsx
function closeSearch() {
  setShowSearch(false);
  setSearchQuery("");
}
```

- [ ] **Step 4: Add search results computation**

After the existing `const activeProjects = ...` line, add:

```tsx
const searchResults = showSearch
  ? projects
      .flatMap((p) => p.conversations.map((c) => ({ ...c, projectId: p.id })))
      .filter((c) => c.title.toLowerCase().includes(searchQuery.toLowerCase()))
      .sort((a, b) => b.createdAt - a.createdAt)
  : [];
```

- [ ] **Step 5: Add `useEffect` for Escape key and auto-focus**

After the existing `useEffect` that focuses the rename input (the one with `[renamingConvId]` dependency), add:

```tsx
// Focus search input and handle Escape key when panel is open
useEffect(() => {
  if (!showSearch) return;
  searchInputRef.current?.focus();
  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") closeSearch();
  }
  document.addEventListener("keydown", handleKeyDown);
  return () => document.removeEventListener("keydown", handleKeyDown);
}, [showSearch]);
```

- [ ] **Step 6: Wire the Search button**

Find the existing Search button:
```tsx
        <button className="sidebar-nav-item" aria-label="Search conversations">
          <Search size={15} strokeWidth={1.8} />
          <span>Search</span>
        </button>
```
Replace with:
```tsx
        <button className="sidebar-nav-item" aria-label="Search conversations" onClick={() => setShowSearch(true)}>
          <Search size={15} strokeWidth={1.8} />
          <span>Search</span>
        </button>
```

- [ ] **Step 7: Add overlay and search panel JSX**

Find the closing `</aside>` tag at the very end of the return statement. Insert the overlay and panel **before** `</aside>`:

```tsx
      {/* Search overlay + panel */}
      {showSearch && (
        <>
          <div className="search-overlay" onClick={closeSearch} />
          <div className="search-panel">
            <div className="search-panel__input-wrap">
              <Search size={15} strokeWidth={1.8} className="search-panel__icon" />
              <input
                ref={searchInputRef}
                className="search-panel__input"
                placeholder="Search chats..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button className="search-panel__clear" onClick={closeSearch} aria-label="Close search">
                <X size={15} strokeWidth={1.8} />
              </button>
            </div>
            <div className="search-panel__list">
              {searchResults.length === 0 && searchQuery.trim() !== "" && (
                <div className="search-panel__empty">No chats found</div>
              )}
              {searchResults.map((conv) => (
                <div
                  key={conv.id}
                  className="search-panel__item"
                  onClick={() => {
                    onSelectConversation(conv.projectId, conv.id);
                    closeSearch();
                  }}
                >
                  <span className="search-panel__item-title">{conv.title}</span>
                  <span className="search-panel__item-time">{relativeTime(conv.createdAt)}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
```

- [ ] **Step 8: Run TypeScript check**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 9: Manual smoke test**

1. Open the app (dev server or Tauri)
2. Click "Search" in the sidebar → panel slides in from the right of the sidebar, input is focused
3. Type part of a chat title → matching results appear in real time
4. Type something with no matches → "No chats found" shown
5. Click a result → navigates to that chat, panel closes
6. Press Escape → panel closes, query cleared
7. Click the X button → panel closes
8. Click outside the panel (overlay area) → panel closes
9. Open panel again → input is empty and focused

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat: wire sidebar search panel"
```
