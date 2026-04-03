# Setup Wizard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the free-text model input with a three-step guided wizard (provider → model → API key) in the ratatui TUI.

**Architecture:** A static `PROVIDERS` registry defines provider/model/env-var mappings. `SetupState` tracks the current step and selection indices. `draw_setup()` renders a different popup for each step. `config.rs` gains `save_with_key()` to persist both model and API key. The Python backend's `SUPPORTED_MODELS` is updated to match.

**Tech Stack:** Rust 2021, ratatui 0.29, crossterm 0.28, toml 0.8, Python/litellm

---

## File Map

**Create:**
- `cli-tui/src/registry.rs` — static `PROVIDERS` array with provider/model/env-var data

**Modify:**
- `cli-tui/src/app.rs` — new `SetupStep`, rewritten `SetupState`, new actions, updated `App::new()` and `App::update()`
- `cli-tui/src/ui.rs` — rewritten `draw_setup()` with three sub-renderers
- `cli-tui/src/main.rs` — add `mod registry`, rewrite `handle_setup_key()`
- `cli-tui/src/config.rs` — add `save_with_key()`, expand `has_api_key()` env var list
- `proteinclaw/core/config.py` — expand `SUPPORTED_MODELS` and `_PROVIDER_KEY_MAP`

---

### Task 1: Provider registry module

**Files:**
- Create: `cli-tui/src/registry.rs`
- Modify: `cli-tui/src/main.rs` (add `mod registry;`)

- [ ] **Step 1: Create `cli-tui/src/registry.rs`**

```rust
pub struct ModelEntry {
    pub name: &'static str,
    /// Display suffix shown in the TUI list (e.g. "★free")
    pub tag: &'static str,
}

pub struct Provider {
    pub name: &'static str,
    pub models: &'static [ModelEntry],
    /// Environment variable name for the API key. Empty string means no key needed.
    pub env_var: &'static str,
}

pub static PROVIDERS: &[Provider] = &[
    Provider {
        name: "OpenAI",
        models: &[ModelEntry { name: "gpt-4o", tag: "" }],
        env_var: "OPENAI_API_KEY",
    },
    Provider {
        name: "Anthropic",
        models: &[ModelEntry { name: "claude-opus-4-5", tag: "" }],
        env_var: "ANTHROPIC_API_KEY",
    },
    Provider {
        name: "Google",
        models: &[
            ModelEntry { name: "gemini-2.5-pro", tag: "" },
            ModelEntry { name: "gemini-2.5-flash", tag: "" },
        ],
        env_var: "GEMINI_API_KEY",
    },
    Provider {
        name: "DeepSeek",
        models: &[
            ModelEntry { name: "deepseek-chat", tag: "" },
            ModelEntry { name: "deepseek-reasoner", tag: "" },
        ],
        env_var: "DEEPSEEK_API_KEY",
    },
    Provider {
        name: "Qwen (DashScope)",
        models: &[
            ModelEntry { name: "qwen-max", tag: "" },
            ModelEntry { name: "qwen-plus", tag: "" },
        ],
        env_var: "DASHSCOPE_API_KEY",
    },
    Provider {
        name: "MiniMax",
        models: &[ModelEntry { name: "minimax-text-01", tag: "" }],
        env_var: "MINIMAX_API_KEY",
    },
    Provider {
        name: "OpenRouter",
        models: &[
            ModelEntry { name: "openrouter/google/gemini-2.5-flash-preview-05-20", tag: "★free" },
            ModelEntry { name: "openrouter/deepseek/deepseek-chat-v3-0324", tag: "★free" },
            ModelEntry { name: "openrouter/meta-llama/llama-4-maverick", tag: "★free" },
            ModelEntry { name: "openrouter/qwen/qwen3-235b-a22b", tag: "★free" },
            ModelEntry { name: "openrouter/auto", tag: "" },
        ],
        env_var: "OPENROUTER_API_KEY",
    },
    Provider {
        name: "Ollama (local)",
        models: &[
            ModelEntry { name: "ollama/llama4", tag: "" },
            ModelEntry { name: "ollama/qwen3", tag: "" },
            ModelEntry { name: "ollama/llama3", tag: "" },
        ],
        env_var: "",
    },
];
```

- [ ] **Step 2: Add `mod registry;` to `main.rs`**

In `cli-tui/src/main.rs`, add `mod registry;` after the existing `mod ws;` line (line 7):

```rust
mod ws;
mod registry;
```

- [ ] **Step 3: Verify it compiles**

Run: `cargo build -p cli-tui 2>&1`
Expected: compiles with warnings about unused items only.

- [ ] **Step 4: Commit**

```bash
git add cli-tui/src/registry.rs cli-tui/src/main.rs
git commit -m "feat(tui): add provider/model registry for setup wizard"
```

---

### Task 2: Rewrite SetupState and Actions in `app.rs`

**Files:**
- Modify: `cli-tui/src/app.rs`

- [ ] **Step 1: Replace SetupField/SetupState (lines 53-68)**

Replace this block:

```rust
// ── Setup wizard state ───────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
pub enum SetupField {
    Model,
    Done,
}

#[derive(Debug, Clone)]
pub struct SetupState {
    #[allow(dead_code)]
    pub field: SetupField,
    pub model_buf: String,
    pub error: Option<String>,
}
```

With:

```rust
// ── Setup wizard state ───────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum SetupStep {
    Provider,
    Model,
    ApiKey,
}

#[derive(Debug, Clone)]
pub struct SetupState {
    pub step: SetupStep,
    pub provider_idx: usize,
    pub model_idx: usize,
    pub key_buf: String,
    pub error: Option<String>,
}
```

- [ ] **Step 2: Replace Action variants (lines 80-102)**

Replace the full `Action` enum with:

```rust
pub enum Action {
    WsConnected,
    WsDisconnected,
    WsEvent(WsEvent),
    SendMessage(String),
    ScrollUp,
    ScrollDown,
    ScrollToBottom,
    ToggleThinking { msg: usize, part: usize },
    ToggleTool { msg: usize, part: usize },
    SetupUp,
    SetupDown,
    SetupNext,
    SetupBack,
    SetupKeyInput(String),
    Quit,
    Tick,
    PopupUp,
    PopupDown,
    PopupClose,
    CommandClear,
    CommandSetModel(String),
    CommandSetSystem(String),
    CommandHelp,
    CommandExport,
}
```

- [ ] **Step 3: Update `App::new()` (lines 122-149)**

Replace the `let needs_setup` and `let screen` block:

```rust
    pub fn new(config: Config) -> Self {
        let needs_setup = !Config::has_api_key();
        let screen = if needs_setup {
            Screen::Setup(SetupState {
                step: SetupStep::Provider,
                provider_idx: 0,
                model_idx: 0,
                key_buf: String::new(),
                error: None,
            })
        } else {
            Screen::Chat
        };
        Self {
            screen,
            config,
            messages: Vec::new(),
            scroll_offset: 0,
            conn_status: ConnStatus::Connecting,
            should_quit: false,
            token_counts: (0, 0),
            current_dir: std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| "~".to_string()),
            tick: 0,
            command_popup: None,
            history: Vec::new(),
        }
    }
```

- [ ] **Step 4: Replace setup action handlers in `App::update()` (lines 194-212)**

Remove the old `Action::SetupModelInput` and `Action::SetupNext` arms. Replace with:

```rust
            Action::SetupUp => {
                if let Screen::Setup(ref mut st) = self.screen {
                    match st.step {
                        SetupStep::Provider => {
                            st.provider_idx = st.provider_idx.saturating_sub(1);
                        }
                        SetupStep::Model => {
                            st.model_idx = st.model_idx.saturating_sub(1);
                        }
                        SetupStep::ApiKey => {}
                    }
                    st.error = None;
                }
            }
            Action::SetupDown => {
                if let Screen::Setup(ref mut st) = self.screen {
                    match st.step {
                        SetupStep::Provider => {
                            let max = crate::registry::PROVIDERS.len().saturating_sub(1);
                            st.provider_idx = (st.provider_idx + 1).min(max);
                        }
                        SetupStep::Model => {
                            let provider = &crate::registry::PROVIDERS[st.provider_idx];
                            let max = provider.models.len().saturating_sub(1);
                            st.model_idx = (st.model_idx + 1).min(max);
                        }
                        SetupStep::ApiKey => {}
                    }
                    st.error = None;
                }
            }
            Action::SetupNext => {
                if let Screen::Setup(ref st) = self.screen.clone() {
                    let provider = &crate::registry::PROVIDERS[st.provider_idx];
                    match st.step {
                        SetupStep::Provider => {
                            if let Screen::Setup(ref mut st) = self.screen {
                                st.step = SetupStep::Model;
                                st.model_idx = 0;
                                st.error = None;
                            }
                        }
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
                        SetupStep::ApiKey => {
                            let key = st.key_buf.trim().to_string();
                            if key.is_empty() {
                                if let Screen::Setup(ref mut st) = self.screen {
                                    st.error = Some("API key cannot be empty.".into());
                                }
                                return;
                            }
                            let model = provider.models[st.model_idx].name.to_string();
                            let env_var = provider.env_var.to_string();
                            self.config.model = model;
                            std::env::set_var(&env_var, &key);
                            let _ = self.config.save_with_key(&env_var, &key);
                            self.screen = Screen::Chat;
                        }
                    }
                }
            }
            Action::SetupBack => {
                if let Screen::Setup(ref mut st) = self.screen {
                    match st.step {
                        SetupStep::Provider => {} // no-op on first step
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
            Action::SetupKeyInput(s) => {
                if let Screen::Setup(ref mut st) = self.screen {
                    st.key_buf = s;
                    st.error = None;
                }
            }
```

- [ ] **Step 5: Verify it compiles**

Run: `cargo build -p cli-tui 2>&1`
Expected: errors about missing `save_with_key` in config.rs and about `draw_setup` / `handle_setup_key` argument types — those are fixed in later tasks.

- [ ] **Step 6: Commit**

```bash
git add cli-tui/src/app.rs
git commit -m "feat(tui): rewrite SetupState for three-step wizard flow"
```

---

### Task 3: Update `config.rs` — `save_with_key()` and expanded `has_api_key()`

**Files:**
- Modify: `cli-tui/src/config.rs`

- [ ] **Step 1: Add `save_with_key()` method after `save()`**

Add this method inside the `impl Config` block, after the existing `save()` method:

```rust
    /// Save config and persist a single API key.
    pub fn save_with_key(&self, env_var: &str, key: &str) -> Result<()> {
        let path = config_path();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let mut existing: TomlFile = if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            toml::from_str(&text).unwrap_or_default()
        } else {
            TomlFile::default()
        };

        existing.keys.insert(env_var.to_string(), key.to_string());
        existing.defaults.model = Some(self.model.clone());

        std::fs::write(&path, toml::to_string(&existing)?)?;
        Ok(())
    }
```

- [ ] **Step 2: Expand `has_api_key()` with new providers**

Replace the `has_api_key()` method:

```rust
    /// Returns true if at least one provider API key is present in the environment.
    pub fn has_api_key() -> bool {
        let keys = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "MINIMAX_API_KEY",
            "GEMINI_API_KEY",
            "DASHSCOPE_API_KEY",
            "OPENROUTER_API_KEY",
        ];
        keys.iter()
            .any(|k| std::env::var(k).map(|v| !v.is_empty()).unwrap_or(false))
    }
```

- [ ] **Step 3: Verify it compiles**

Run: `cargo build -p cli-tui 2>&1`
Expected: compiles (may still have errors in ui.rs/main.rs from old SetupState references).

- [ ] **Step 4: Commit**

```bash
git add cli-tui/src/config.rs
git commit -m "feat(config): add save_with_key and expand provider key list"
```

---

### Task 4: Rewrite `draw_setup()` in `ui.rs`

**Files:**
- Modify: `cli-tui/src/ui.rs`

- [ ] **Step 1: Update imports at top of `ui.rs`**

Replace:

```rust
use crate::app::{App, Screen, SetupState};
```

With:

```rust
use crate::app::{App, Screen, SetupState, SetupStep};
use crate::registry::PROVIDERS;
```

- [ ] **Step 2: Replace entire `draw_setup()` function (lines 70-128)**

Replace the existing `fn draw_setup` with:

```rust
fn draw_setup(f: &mut Frame, st: &SetupState) {
    let area = f.area();
    let popup_h: u16 = match st.step {
        SetupStep::Provider => (PROVIDERS.len() as u16 + 6).min(area.height),
        SetupStep::Model => {
            let n = PROVIDERS[st.provider_idx].models.len() as u16;
            (n + 8).min(area.height)
        }
        SetupStep::ApiKey => 12u16.min(area.height),
    };
    let popup_w: u16 = 50.min(area.width);
    let vpad = area.height.saturating_sub(popup_h) / 2;
    let hpad = area.width.saturating_sub(popup_w) / 2;
    let popup = Rect { x: hpad, y: vpad, width: popup_w, height: popup_h };

    f.render_widget(Clear, popup);

    let title = match st.step {
        SetupStep::Provider => " Setup — 1/3 Provider ",
        SetupStep::Model    => " Setup — 2/3 Model ",
        SetupStep::ApiKey   => " Setup — 3/3 API Key ",
    };
    let block = Block::default()
        .title(title)
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::Cyan));
    f.render_widget(block, popup);

    let inner = Rect {
        x: popup.x + 2,
        y: popup.y + 1,
        width: popup.width.saturating_sub(4),
        height: popup.height.saturating_sub(2),
    };

    match st.step {
        SetupStep::Provider => draw_setup_provider(f, inner, st),
        SetupStep::Model    => draw_setup_model(f, inner, st),
        SetupStep::ApiKey   => draw_setup_api_key(f, inner, st),
    }
}

fn draw_setup_provider(f: &mut Frame, area: Rect, st: &SetupState) {
    let mut lines: Vec<Line> = vec![
        Line::from(Span::styled("Select a provider:", Style::default().fg(Color::Yellow))),
        Line::raw(""),
    ];
    for (i, p) in PROVIDERS.iter().enumerate() {
        let marker = if i == st.provider_idx { "> " } else { "  " };
        let style = if i == st.provider_idx {
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
        } else {
            Style::default()
        };
        lines.push(Line::from(Span::styled(format!("{}{}", marker, p.name), style)));
    }
    lines.push(Line::raw(""));
    lines.push(Line::from(vec![
        Span::styled("[↑↓]", Style::default().fg(Color::Cyan)),
        Span::raw(" select  "),
        Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
        Span::raw(" confirm"),
    ]));
    if let Some(err) = &st.error {
        lines.push(Line::from(Span::styled(err.as_str(), Style::default().fg(Color::Red))));
    }
    f.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), area);
}

fn draw_setup_model(f: &mut Frame, area: Rect, st: &SetupState) {
    let provider = &PROVIDERS[st.provider_idx];
    let mut lines: Vec<Line> = vec![
        Line::from(vec![
            Span::raw("Provider: "),
            Span::styled(provider.name, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(Span::styled("Select a model:", Style::default().fg(Color::Yellow))),
        Line::raw(""),
    ];
    for (i, m) in provider.models.iter().enumerate() {
        let marker = if i == st.model_idx { "> " } else { "  " };
        let style = if i == st.model_idx {
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
        } else {
            Style::default()
        };
        let label = if m.tag.is_empty() {
            m.name.to_string()
        } else {
            format!("{} {}", m.name, m.tag)
        };
        lines.push(Line::from(Span::styled(format!("{}{}", marker, label), style)));
    }
    lines.push(Line::raw(""));
    lines.push(Line::from(vec![
        Span::styled("[↑↓]", Style::default().fg(Color::Cyan)),
        Span::raw(" select  "),
        Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
        Span::raw(" confirm  "),
        Span::styled("[Esc]", Style::default().fg(Color::Cyan)),
        Span::raw(" back"),
    ]));
    if let Some(err) = &st.error {
        lines.push(Line::from(Span::styled(err.as_str(), Style::default().fg(Color::Red))));
    }
    f.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), area);
}

fn draw_setup_api_key(f: &mut Frame, area: Rect, st: &SetupState) {
    let provider = &PROVIDERS[st.provider_idx];
    let model = &provider.models[st.model_idx];

    // Mask key: show first 6 chars, rest as asterisks
    let masked = if st.key_buf.len() <= 6 {
        st.key_buf.clone()
    } else {
        let visible = &st.key_buf[..6];
        format!("{}{}", visible, "*".repeat(st.key_buf.len() - 6))
    };

    let mut lines: Vec<Line> = vec![
        Line::from(vec![
            Span::raw("Provider: "),
            Span::styled(provider.name, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::raw("Model:    "),
            Span::styled(model.name, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]),
        Line::raw(""),
        Line::from(Span::styled(
            format!("Enter your {}:", provider.env_var),
            Style::default().fg(Color::Yellow),
        )),
        Line::from(vec![
            Span::styled(&masked, Style::default().fg(Color::White)),
            Span::styled("_", Style::default().fg(Color::Green).add_modifier(Modifier::SLOW_BLINK)),
        ]),
        Line::raw(""),
        Line::from(vec![
            Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
            Span::raw(" save  "),
            Span::styled("[Esc]", Style::default().fg(Color::Cyan)),
            Span::raw(" back"),
        ]),
    ];
    if let Some(err) = &st.error {
        lines.push(Line::from(Span::styled(err.as_str(), Style::default().fg(Color::Red))));
    }
    f.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), area);
}
```

- [ ] **Step 3: Verify it compiles**

Run: `cargo build -p cli-tui 2>&1`
Expected: may still fail on `handle_setup_key` in main.rs — fixed in Task 5.

- [ ] **Step 4: Commit**

```bash
git add cli-tui/src/ui.rs
git commit -m "feat(tui): render three-step setup wizard UI"
```

---

### Task 5: Rewrite `handle_setup_key()` in `main.rs`

**Files:**
- Modify: `cli-tui/src/main.rs`

- [ ] **Step 1: Replace `handle_setup_key` function (lines 288-309)**

Replace the entire function with:

```rust
fn handle_setup_key(key: event::KeyEvent, app: &mut App) {
    if let Screen::Setup(ref st) = app.screen {
        match st.step {
            app::SetupStep::Provider | app::SetupStep::Model => {
                match key.code {
                    KeyCode::Up => app.update(Action::SetupUp),
                    KeyCode::Down => app.update(Action::SetupDown),
                    KeyCode::Enter => app.update(Action::SetupNext),
                    KeyCode::Esc => app.update(Action::SetupBack),
                    _ => {}
                }
            }
            app::SetupStep::ApiKey => {
                match key.code {
                    KeyCode::Enter => app.update(Action::SetupNext),
                    KeyCode::Esc => app.update(Action::SetupBack),
                    KeyCode::Char(c) => {
                        let mut buf = st.key_buf.clone();
                        buf.push(c);
                        app.update(Action::SetupKeyInput(buf));
                    }
                    KeyCode::Backspace => {
                        let mut buf = st.key_buf.clone();
                        buf.pop();
                        app.update(Action::SetupKeyInput(buf));
                    }
                    _ => {}
                }
            }
        }
    }
}
```

- [ ] **Step 2: Build and verify**

Run: `cargo build -p cli-tui 2>&1`
Expected: PASS — all Rust files should compile cleanly now.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/main.rs
git commit -m "feat(tui): rewrite setup key handler for wizard navigation"
```

---

### Task 6: Update Python backend `SUPPORTED_MODELS`

**Files:**
- Modify: `proteinclaw/core/config.py`

- [ ] **Step 1: Replace `SUPPORTED_MODELS` dict (lines 8-15)**

Replace:

```python
SUPPORTED_MODELS: dict[str, dict] = {
    "gpt-4o":            {"provider": "openai"},
    "claude-opus-4-5":   {"provider": "anthropic"},
    "deepseek-chat":     {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner": {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "minimax-text-01":   {"provider": "openai",    "api_base": "https://api.minimax.chat/v1"},
    "ollama/llama3":     {"provider": "ollama",    "api_base": "http://localhost:11434"},
}
```

With:

```python
SUPPORTED_MODELS: dict[str, dict] = {
    # OpenAI
    "gpt-4o":            {"provider": "openai"},
    # Anthropic
    "claude-opus-4-5":   {"provider": "anthropic"},
    # Google
    "gemini-2.5-pro":    {"provider": "google",   "api_base": "https://generativelanguage.googleapis.com/v1beta/openai"},
    "gemini-2.5-flash":  {"provider": "google",   "api_base": "https://generativelanguage.googleapis.com/v1beta/openai"},
    # DeepSeek
    "deepseek-chat":     {"provider": "deepseek", "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner": {"provider": "deepseek", "api_base": "https://api.deepseek.com"},
    # Qwen (DashScope)
    "qwen-max":          {"provider": "openai",   "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "qwen-plus":         {"provider": "openai",   "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    # MiniMax
    "minimax-text-01":   {"provider": "openai",   "api_base": "https://api.minimax.chat/v1"},
    # OpenRouter
    "openrouter/google/gemini-2.5-flash-preview-05-20": {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/deepseek/deepseek-chat-v3-0324":        {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/meta-llama/llama-4-maverick":            {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/qwen/qwen3-235b-a22b":                  {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/auto":   {"provider": "openai",   "api_base": "https://openrouter.ai/api/v1"},
    # Ollama (local)
    "ollama/llama4":     {"provider": "ollama",   "api_base": "http://localhost:11434"},
    "ollama/qwen3":      {"provider": "ollama",   "api_base": "http://localhost:11434"},
    "ollama/llama3":     {"provider": "ollama",   "api_base": "http://localhost:11434"},
}
```

- [ ] **Step 2: Add new entries to `_PROVIDER_KEY_MAP` (lines 35-40)**

Replace:

```python
_PROVIDER_KEY_MAP: dict[str, str] = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
    "minimax":   "MINIMAX_API_KEY",
}
```

With:

```python
_PROVIDER_KEY_MAP: dict[str, str] = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google":    "GEMINI_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
    "minimax":   "MINIMAX_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "openrouter":"OPENROUTER_API_KEY",
}
```

Note: Qwen and OpenRouter models use `provider: "openai"` in `SUPPORTED_MODELS` because they expose OpenAI-compatible endpoints. The `_PROVIDER_KEY_MAP` entries for `"dashscope"` and `"openrouter"` are used only by the `needs_setup()` function for checking if a key is configured — the actual API auth is handled by litellm using the env var + `api_base`.

- [ ] **Step 3: Commit**

```bash
git add proteinclaw/core/config.py
git commit -m "feat(backend): expand SUPPORTED_MODELS with new providers"
```

---

### Task 7: Smoke test

**Files:** (none — manual verification)

- [ ] **Step 1: Full build**

Run: `cargo build -p cli-tui 2>&1`
Expected: compiles cleanly (warnings OK).

- [ ] **Step 2: Run the TUI**

Run: `cargo run -p cli-tui`

Verify:
1. Setup wizard opens at Step 1 (Provider list with 8 entries)
2. `Up/Down` moves the highlight, `Enter` advances to Step 2
3. Step 2 shows models for the selected provider (with `★free` tags on OpenRouter items)
4. `Esc` goes back to Step 1
5. Selecting an Ollama model + `Enter` goes directly to Chat (no API key step)
6. Selecting any non-Ollama model + `Enter` goes to Step 3 (API key input)
7. Typing a key shows masked characters, `Enter` saves and transitions to Chat
8. `Ctrl+C` quits at any step

- [ ] **Step 3: Verify config file**

After completing setup, check `~/.config/proteinclaw/config.toml` contains the selected model and key.

Run: `cat ~/.config/proteinclaw/config.toml`
Expected: `[keys]` section with the entered key, `[defaults]` section with the selected model.

- [ ] **Step 4: Verify skip on re-launch**

Run the TUI again: `cargo run -p cli-tui`
Expected: Skips setup and goes directly to Chat screen (because key is now saved).
