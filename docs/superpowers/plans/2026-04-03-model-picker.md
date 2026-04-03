# /model Picker Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `/model` is typed without arguments in Chat, open the existing provider/model setup wizard so users can switch providers and models mid-session.

**Architecture:** Add a `WizardMode` enum (`FirstRun` | `SwitchModel`) to the existing `SetupState` struct. Two small behavioral branches keyed on this mode: (1) Esc on Provider step cancels back to Chat in `SwitchModel` mode, (2) confirmed Model step skips the key input if the provider's key is already set. Entry point is the `/model` no-arg branch in `handle_chat_key`.

**Tech Stack:** Rust, ratatui, crossterm. All changes are in `cli-tui/src/`.

---

## File Map

| File | Change |
|------|--------|
| `cli-tui/src/app.rs` | Add `WizardMode` enum; add `mode` field to `SetupState`; update `App::new`, `SetupBack`, `SetupNext` |
| `cli-tui/src/main.rs` | Change `/model` no-arg branch to open wizard |
| `cli-tui/src/ui.rs` | Show `[Esc] cancel` hint in Provider step when `SwitchModel` |

---

## Task 1: Add `WizardMode` to `app.rs`

**Files:**
- Modify: `cli-tui/src/app.rs`

- [ ] **Step 1: Add the `WizardMode` enum** after the `SetupStep` enum (around line 56):

```rust
#[derive(Debug, Clone, PartialEq)]
pub enum WizardMode {
    FirstRun,
    SwitchModel,
}
```

- [ ] **Step 2: Add `mode` field to `SetupState`** (around line 63):

Replace:
```rust
pub struct SetupState {
    pub step: SetupStep,
    pub provider_idx: usize,
    pub model_idx: usize,
    pub key_buf: String,
    pub error: Option<String>,
}
```
With:
```rust
pub struct SetupState {
    pub step: SetupStep,
    pub provider_idx: usize,
    pub model_idx: usize,
    pub key_buf: String,
    pub error: Option<String>,
    pub mode: WizardMode,
}
```

- [ ] **Step 3: Add `mode: WizardMode::FirstRun` to `App::new`** (around line 130):

Replace:
```rust
Screen::Setup(SetupState {
    step: SetupStep::Provider,
    provider_idx: 0,
    model_idx: 0,
    key_buf: String::new(),
    error: None,
})
```
With:
```rust
Screen::Setup(SetupState {
    step: SetupStep::Provider,
    provider_idx: 0,
    model_idx: 0,
    key_buf: String::new(),
    error: None,
    mode: WizardMode::FirstRun,
})
```

- [ ] **Step 4: Update `SetupBack` handler** — in `App::update`, find the `Action::SetupBack` arm. Replace the `SetupStep::Provider` branch (around line 278):

Replace:
```rust
SetupStep::Provider => {} // no-op on first step
```
With:
```rust
SetupStep::Provider => {
    if st.mode == WizardMode::SwitchModel {
        self.screen = Screen::Chat;
    }
    // FirstRun: no-op
}
```

Note: the borrow checker requires reading `st.mode` before mutating `self.screen`. The existing pattern in `SetupBack` already uses `if let Screen::Setup(ref mut st)` — adjust to read mode first:

```rust
Action::SetupBack => {
    let mode = if let Screen::Setup(ref st) = self.screen {
        st.mode.clone()
    } else {
        return;
    };
    if let Screen::Setup(ref mut st) = self.screen {
        match st.step {
            SetupStep::Provider => {
                if mode == WizardMode::SwitchModel {
                    self.screen = Screen::Chat;
                }
                // FirstRun: no-op
            }
            SetupStep::Model => {
                st.step = SetupStep::Provider;
                st.error = None;
            }
            SetupStep::ApiKey => {
                st.step = SetupStep::Model;
                st.error = None;
            }
        }
    }
}
```

- [ ] **Step 5: Update `SetupNext` on Model step** — in `App::update`, find the `Action::SetupNext` arm, `SetupStep::Model` branch (around line 243). Replace:

```rust
SetupStep::Model => {
    // Ollama needs no key — skip to Chat
    if provider.env_var.is_empty() {
        let model = provider.models[st.model_idx].name.to_string();
        self.config.model = model;
        let _ = self.config.save();
        self.screen = Screen::Chat;
    } else {
        if let Screen::Setup(ref mut st) = self.screen {
            st.step = SetupStep::ApiKey;
            st.key_buf.clear();
            st.error = None;
        }
    }
}
```
With:
```rust
SetupStep::Model => {
    let key_already_set = !provider.env_var.is_empty()
        && std::env::var(provider.env_var)
            .map(|v| !v.is_empty())
            .unwrap_or(false);
    let skip_key = provider.env_var.is_empty()
        || (st.mode == WizardMode::SwitchModel && key_already_set);

    if skip_key {
        let model = provider.models[st.model_idx].name.to_string();
        self.config.model = model;
        let _ = self.config.save();
        self.screen = Screen::Chat;
    } else {
        if let Screen::Setup(ref mut st) = self.screen {
            st.step = SetupStep::ApiKey;
            st.key_buf.clear();
            st.error = None;
        }
    }
}
```

- [ ] **Step 6: Verify it compiles**

```bash
cd cli-tui && cargo check 2>&1
```
Expected: no errors (only possible warnings about unused import if any).

- [ ] **Step 7: Commit**

```bash
git add cli-tui/src/app.rs
git commit -m "feat: add WizardMode to SetupState for /model picker"
```

---

## Task 2: Open wizard from `/model` command in `main.rs`

**Files:**
- Modify: `cli-tui/src/main.rs`

- [ ] **Step 1: Add `WizardMode` to the import** at the top of `main.rs`. Find:

```rust
use app::{Action, App, Screen};
```
Change to:
```rust
use app::{Action, App, Screen, SetupState, SetupStep, WizardMode};
```

- [ ] **Step 2: Change the `/model` no-arg branch** in `handle_chat_key` (around line 235):

Replace:
```rust
"/model"  => {
    let model = rest.trim().to_string();
    if !model.is_empty() {
        app.update(Action::CommandSetModel(model));
    } else {
        app.messages.push(crate::app::ChatMessage::Error(
            format!("Usage: /model <name>  (current: {})", app.config.model),
        ));
    }
}
```
With:
```rust
"/model"  => {
    let model = rest.trim().to_string();
    if !model.is_empty() {
        app.update(Action::CommandSetModel(model));
    } else {
        app.screen = Screen::Setup(SetupState {
            step: SetupStep::Provider,
            provider_idx: 0,
            model_idx: 0,
            key_buf: String::new(),
            error: None,
            mode: WizardMode::SwitchModel,
        });
        app.command_popup = None;
    }
}
```

- [ ] **Step 3: Verify it compiles**

```bash
cd cli-tui && cargo check 2>&1
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add cli-tui/src/main.rs
git commit -m "feat: /model with no args opens provider picker wizard"
```

---

## Task 3: Show `[Esc] cancel` hint in Provider step UI

**Files:**
- Modify: `cli-tui/src/ui.rs`

- [ ] **Step 1: Update `draw_setup_provider`** to add the Esc hint when in `SwitchModel` mode. The function signature is `fn draw_setup_provider(f: &mut Frame, area: Rect, st: &SetupState)`. Find the footer lines block (around line 128):

Replace:
```rust
lines.push(Line::from(vec![
    Span::styled("[↑↓]", Style::default().fg(Color::Cyan)),
    Span::raw(" select  "),
    Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
    Span::raw(" confirm"),
]));
```
With:
```rust
let mut footer = vec![
    Span::styled("[↑↓]", Style::default().fg(Color::Cyan)),
    Span::raw(" select  "),
    Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
    Span::raw(" confirm"),
];
if st.mode == WizardMode::SwitchModel {
    footer.push(Span::raw("  "));
    footer.push(Span::styled("[Esc]", Style::default().fg(Color::Cyan)));
    footer.push(Span::raw(" cancel"));
}
lines.push(Line::from(footer));
```

- [ ] **Step 2: Add `WizardMode` to the import in `ui.rs`**. Find:

```rust
use crate::app::{App, Screen, SetupState, SetupStep};
```
Change to:
```rust
use crate::app::{App, Screen, SetupState, SetupStep, WizardMode};
```

- [ ] **Step 3: Verify it compiles**

```bash
cd cli-tui && cargo check 2>&1
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add cli-tui/src/ui.rs
git commit -m "feat: show [Esc] cancel hint in provider step for SwitchModel mode"
```

---

## Task 4: Final build and smoke test

- [ ] **Step 1: Full build**

```bash
cd cli-tui && cargo build 2>&1
```
Expected: compiles cleanly.

- [ ] **Step 2: Manual smoke test checklist**

Launch the TUI and verify:
1. On first launch with no config, the wizard starts as before (Provider step, no Esc hint)
2. After setup, in Chat: type `/model` + Enter → wizard opens with `[Esc] cancel` visible
3. Press `Esc` → returns to Chat, model unchanged
4. Open `/model` again, select a provider whose key is already saved → after choosing model, goes directly to Chat (no key step)
5. Open `/model`, select a provider with no key saved → key input step appears, entering a key saves it and returns to Chat
6. After switching, the chat history is preserved (existing messages still visible)
7. `/model gpt-4o` (with arg) still works as before

- [ ] **Step 3: Commit if any fixups were needed**

```bash
git add -p
git commit -m "fix: <describe any fixup>"
```
