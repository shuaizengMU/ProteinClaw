# /model Picker Wizard Design

**Date:** 2026-04-03
**Goal:** When the user types `/model` (no arguments) in Chat, open the existing provider/model setup wizard so they can switch providers and models mid-session.

---

## Behavior Summary

- `/model <name>` (with argument) — unchanged: sets model directly
- `/model` (no argument) — opens the 3-step provider/model wizard
- Wizard is the existing `Screen::Setup` flow, distinguished by a new `WizardMode::SwitchModel` variant
- On confirm: new model + provider saved to disk, chat history preserved
- On Esc at Provider step: return to Chat with no changes

---

## State Model (`app.rs`)

Add `WizardMode` enum and a `mode` field to `SetupState`:

```rust
#[derive(Debug, Clone, PartialEq)]
pub enum WizardMode {
    FirstRun,    // launched on startup when no API key exists
    SwitchModel, // launched via /model from Chat
}

pub struct SetupState {
    pub step: SetupStep,
    pub provider_idx: usize,
    pub model_idx: usize,
    pub key_buf: String,
    pub error: Option<String>,
    pub mode: WizardMode,  // ← new
}
```

Existing `SetupStep` enum and actions (`SetupUp`, `SetupDown`, `SetupNext`, `SetupBack`, `SetupKeyInput`) are unchanged.

---

## Behavioral Differences by Mode

Two conditions branch on `mode`:

### 1. `SetupBack` on Provider step

```rust
SetupStep::Provider => {
    match st.mode {
        WizardMode::SwitchModel => self.screen = Screen::Chat, // cancel → back to Chat
        WizardMode::FirstRun => {}                              // no-op
    }
}
```

### 2. `SetupNext` on Model step — skip key step if already set

```rust
SetupStep::Model => {
    let key_already_set = !provider.env_var.is_empty()
        && std::env::var(provider.env_var)
            .map(|v| !v.is_empty())
            .unwrap_or(false);

    if provider.env_var.is_empty() || (st.mode == WizardMode::SwitchModel && key_already_set) {
        // Ollama (no key needed) OR switching to a provider whose key is already saved
        let model = provider.models[st.model_idx].name.to_string();
        self.config.model = model;
        let _ = self.config.save();
        self.screen = Screen::Chat;
    } else {
        // Advance to ApiKey step
        if let Screen::Setup(ref mut st) = self.screen {
            st.step = SetupStep::ApiKey;
            st.key_buf.clear();
            st.error = None;
        }
    }
}
```

`SetupNext` on `ApiKey` step is unchanged — saves key + model to disk, transitions to Chat.

---

## Initialization (`app.rs` — `App::new`)

The existing `SetupState` construction in `App::new()` must be updated to include the new field:

```rust
Screen::Setup(SetupState {
    step: SetupStep::Provider,
    provider_idx: 0,
    model_idx: 0,
    key_buf: String::new(),
    error: None,
    mode: WizardMode::FirstRun,  // ← add this
})
```

---

## Entry Point (`main.rs`)

Change the `/model` (no-arg) branch in `handle_chat_key()`:

```rust
"/model" => {
    let model = rest.trim().to_string();
    if !model.is_empty() {
        app.update(Action::CommandSetModel(model));
    } else {
        // Open provider/model wizard
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

---

## UI (`ui.rs`)

No structural changes to `draw_setup()`. One addition: when `mode == SwitchModel`, the Provider step footer shows `[Esc] cancel` (since Esc now navigates back to Chat):

```
[Up/Down] select  [Enter] confirm  [Esc] cancel
```

In `FirstRun` mode the footer remains as-is (no Esc hint, since Esc is a no-op there).

---

## Config Persistence

On confirm, `Config::save()` or `Config::save_with_key()` is called — same as the first-run flow. The new model and any newly entered key are written to `~/.config/proteinclaw/config.toml`.

Chat history (`app.messages`, `app.history`) is not touched — preserved across model switches.

---

## Change Summary

| File | Change | Size |
|------|--------|------|
| `app.rs` | Add `WizardMode` enum; add `mode` field to `SetupState`; update `SetupBack` and `SetupNext` logic | ~25 lines |
| `main.rs` | Change `/model` no-arg branch to open wizard | ~10 lines |
| `ui.rs` | Conditionally show `[Esc] cancel` in Provider step footer | ~5 lines |
