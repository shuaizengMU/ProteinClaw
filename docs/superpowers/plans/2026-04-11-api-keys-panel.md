# API Keys 配置面板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "API Keys" entry in the Settings menu that slides open a 240px panel next to the Sidebar where users can view and edit their provider API keys with auto-save on blur.

**Architecture:** A new self-contained `ApiKeysPanel` component reads/writes `localStorage` directly. `App.tsx` manages `showApiKeys` boolean state and renders the panel inside `.app-layout`. `Sidebar.tsx` receives an `onOpenApiKeys` callback and exposes it as a new Settings menu item.

**Tech Stack:** React 19, TypeScript, lucide-react (Key icon), CSS custom properties already defined in `index.css`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/components/ApiKeysPanel.tsx` | Full panel UI, localStorage read/write |
| Modify | `frontend/src/index.css` | Panel styles + slide animation |
| Modify | `frontend/src/components/Sidebar.tsx` | Add `onOpenApiKeys` prop + menu item |
| Modify | `frontend/src/App.tsx` | `showApiKeys` state + render panel |

---

### Task 1: Create `ApiKeysPanel.tsx`

**Files:**
- Create: `frontend/src/components/ApiKeysPanel.tsx`

- [ ] **Step 1: Create the component file**

```tsx
import { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";

const PROVIDERS = [
  { label: "Anthropic", storageKey: "ANTHROPIC_API_KEY" },
  { label: "OpenAI",    storageKey: "OPENAI_API_KEY" },
  { label: "DeepSeek",  storageKey: "DEEPSEEK_API_KEY" },
  { label: "Google",    storageKey: "GEMINI_API_KEY" },
] as const;

function maskKey(value: string): string {
  if (!value) return "";
  if (value.length <= 6) return "••••••";
  return value.slice(0, 6) + "••••••••";
}

interface Props {
  onClose: () => void;
}

export function ApiKeysPanel({ onClose }: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function handleFocus(storageKey: string) {
    setEditing(storageKey);
    setEditValue(localStorage.getItem(storageKey) ?? "");
  }

  function handleBlur(storageKey: string) {
    const trimmed = editValue.trim();
    if (trimmed) {
      localStorage.setItem(storageKey, trimmed);
    } else {
      localStorage.removeItem(storageKey);
    }
    setEditing(null);
    setEditValue("");
  }

  return (
    <div className="api-keys-panel">
      <div className="api-keys-panel-header">
        <button
          className="api-keys-panel-back"
          onClick={onClose}
          aria-label="Close API Keys panel"
        >
          <ArrowLeft size={15} strokeWidth={1.8} />
        </button>
        <span className="api-keys-panel-title">API Keys</span>
      </div>

      <div className="api-keys-panel-body">
        {PROVIDERS.map(({ label, storageKey }) => {
          const saved = localStorage.getItem(storageKey) ?? "";
          const isEditing = editing === storageKey;
          return (
            <div key={storageKey} className="api-keys-provider">
              <label className="api-keys-provider-label">{label}</label>
              <input
                className="api-keys-provider-input"
                type="text"
                value={isEditing ? editValue : maskKey(saved)}
                placeholder="点击输入..."
                readOnly={!isEditing}
                onFocus={() => handleFocus(storageKey)}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={() => handleBlur(storageKey)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /path/to/ProteinClaw/frontend && npx tsc --noEmit
```
Expected: no errors related to `ApiKeysPanel.tsx`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ApiKeysPanel.tsx
git commit -m "feat: add ApiKeysPanel component"
```

---

### Task 2: Add panel styles to `index.css`

**Files:**
- Modify: `frontend/src/index.css` (append at end of file)

- [ ] **Step 1: Append styles**

Add at the very end of `frontend/src/index.css`:

```css
/* ── API Keys Panel ──────────────────────────────────────── */
.api-keys-panel {
  width: 240px;
  flex-shrink: 0;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  animation: slideInPanel 250ms ease;
}

@keyframes slideInPanel {
  from { transform: translateX(-100%); opacity: 0; }
  to   { transform: translateX(0);     opacity: 1; }
}

.api-keys-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 12px 12px;
  border-bottom: 1px solid var(--border-light);
}

.api-keys-panel-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: transparent;
  border: none;
  color: var(--text);
  cursor: pointer;
  transition: background 120ms, color 120ms;
}

.api-keys-panel-back:hover {
  background: var(--border);
  color: var(--text-h);
}

.api-keys-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-h);
}

.api-keys-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.api-keys-provider {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.api-keys-provider-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-xs);
}

.api-keys-provider-input {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 12px;
  font-family: var(--mono);
  color: var(--text-h);
  width: 100%;
  box-sizing: border-box;
  transition: border-color 150ms, box-shadow 150ms;
}

.api-keys-provider-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-bg);
}

.api-keys-provider-input::placeholder {
  color: var(--text-xs);
  font-family: var(--sans);
  font-style: italic;
}

@media (max-width: 768px) {
  .api-keys-panel {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 200;
    height: 100vh;
  }
}
```

- [ ] **Step 2: Verify styles load without error**

Start the dev server and open http://localhost:5173 — no console errors.

```bash
cd /path/to/ProteinClaw && sh scripts/run_frontend.sh
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: add API keys panel styles"
```

---

### Task 3: Update `Sidebar.tsx` — add `onOpenApiKeys` prop and menu item

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Add `Key` to lucide-react imports**

In `frontend/src/components/Sidebar.tsx`, find the lucide-react import line and add `Key`:

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
} from "lucide-react";
```

- [ ] **Step 2: Add `onOpenApiKeys` to the Props interface**

Find the `interface Props` block and add the new prop:

```tsx
interface Props {
  projects: Project[];
  activeConversationId: string | null;
  onSelectConversation: (projectId: string, conversationId: string) => void;
  onNewChat: () => void;
  isOpen?: boolean;
  theme?: 'light' | 'dark' | 'system';
  onThemeChange?: (theme: 'light' | 'dark' | 'system') => void;
  onOpenApiKeys?: () => void;
}
```

- [ ] **Step 3: Destructure `onOpenApiKeys` in the function signature**

Find:
```tsx
export function Sidebar({
  projects,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  isOpen = false,
  theme = 'system',
  onThemeChange,
}: Props) {
```

Replace with:
```tsx
export function Sidebar({
  projects,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  isOpen = false,
  theme = 'system',
  onThemeChange,
  onOpenApiKeys,
}: Props) {
```

- [ ] **Step 4: Add "API Keys" menu item above "Appearance"**

Find the Settings dropdown JSX — specifically the `<div className="sidebar-project-menu"` that appears inside the `{showSettings && (` block. Add the API Keys button **before** the Appearance button:

```tsx
{showSettings && (
  <div
    className="sidebar-project-menu"
    style={{
      bottom: '100%',
      top: 'auto',
      marginBottom: '4px',
      opacity: isSettingsClosing ? 0 : 1,
      transition: 'opacity 300ms ease-out',
    }}
  >
    <button
      className="sidebar-menu-item"
      onClick={() => {
        setShowSettings(false);
        onOpenApiKeys?.();
      }}
    >
      <Key size={13} strokeWidth={1.8} />
      <span>API Keys</span>
    </button>
    <button
      className="sidebar-menu-item"
      onClick={() => setShowAppearance(!showAppearance)}
    >
      {/* ... existing Appearance content unchanged ... */}
    </button>
    {/* ... existing appearance submenu unchanged ... */}
  </div>
)}
```

> Note: Only add the new button — leave the existing Appearance button and submenu exactly as-is.

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd /path/to/ProteinClaw/frontend && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat: add API Keys entry in Settings menu"
```

---

### Task 4: Update `App.tsx` — wire up state and render panel

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Import `ApiKeysPanel`**

At the top of `frontend/src/App.tsx`, add:

```tsx
import { ApiKeysPanel } from "./components/ApiKeysPanel";
```

- [ ] **Step 2: Add `showApiKeys` state**

Inside the `App` component, after the existing `useState` declarations, add:

```tsx
const [showApiKeys, setShowApiKeys] = useState(false);
```

- [ ] **Step 3: Pass `onOpenApiKeys` to `<Sidebar>`**

Find the `<Sidebar ... />` JSX and add the new prop:

```tsx
<Sidebar
  projects={projects}
  activeConversationId={activeConversationId}
  onSelectConversation={(projectId, convId) => {
    selectConversation(projectId, convId);
    setSidebarOpen(false);
  }}
  onNewChat={() => {
    handleNewChat();
    setSidebarOpen(false);
  }}
  isOpen={sidebarOpen}
  theme={theme}
  onThemeChange={setTheme}
  onOpenApiKeys={() => setShowApiKeys(true)}
/>
```

- [ ] **Step 4: Render `<ApiKeysPanel>` inside `.app-layout`**

Find the `return` block. Inside `<div className="app-layout">`, add the panel between `<Sidebar>` and `<ChatWindow>`:

```tsx
return (
  <div className="app-layout">
    <Sidebar
      {/* ... props unchanged ... */}
    />
    {showApiKeys && (
      <ApiKeysPanel onClose={() => setShowApiKeys(false)} />
    )}
    <ChatWindow
      {/* ... props unchanged ... */}
    />
  </div>
);
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd /path/to/ProteinClaw/frontend && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire ApiKeysPanel into app layout"
```

---

### Task 5: Manual verification

- [ ] **Step 1: Start backend + app**

```bash
# Terminal 1
sh scripts/run_backend.sh

# Terminal 2
sh scripts/run_app.sh
```

- [ ] **Step 2: Verify Settings menu shows "API Keys"**

Click the Settings button in the sidebar footer. Confirm the dropdown shows "API Keys" above "Appearance".

- [ ] **Step 3: Verify panel slides in**

Click "API Keys". Confirm a 240px panel slides in from the left showing 4 provider rows: Anthropic, OpenAI, DeepSeek, Google.

- [ ] **Step 4: Verify editing and auto-save**

Click the DeepSeek input. Type a test value (e.g. `sk-test123`). Click outside the field. Open browser DevTools → Application → Local Storage → confirm `DEEPSEEK_API_KEY` = `sk-test123`.

- [ ] **Step 5: Verify masked display**

Close and reopen the panel. Confirm the DeepSeek field shows `sk-tes••••••••` (first 6 chars + bullets).

- [ ] **Step 6: Verify clear on empty**

Click the DeepSeek field, clear it, click outside. Confirm `DEEPSEEK_API_KEY` is removed from localStorage.

- [ ] **Step 7: Verify ESC closes panel**

Open the panel, press ESC. Confirm panel slides out.

- [ ] **Step 8: Verify chat remains usable while panel is open**

Open the panel, then send a message in the chat. Confirm it works normally.
