# vtcode-style TUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `cli-tui/` from a single `ui.rs` into a widget-based layout matching vtcode's visual design: Header / Transcript / Input / Footer, three adaptive layout modes, Wide-mode Tool Call sidebar, and a `/`-triggered command popup.

**Architecture:** `ui.rs` becomes a pure layout orchestrator that detects terminal width and dispatches rendering to focused widget modules in `src/widgets/`. App state gains token counts, current dir, a tick counter, and command popup state.

**Tech Stack:** Rust, ratatui 0.29, crossterm 0.28, tui-textarea 0.7, dirs 5, pulldown-cmark 0.13

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `cli-tui/src/app.rs` | Modify | Add `token_counts`, `current_dir`, `tick`, `command_popup`; new `Action` variants |
| `cli-tui/src/events.rs` | Modify | Add `WsEvent::TokenUsage` variant |
| `cli-tui/src/ui.rs` | Rewrite | Layout orchestrator only — detect mode, call widgets |
| `cli-tui/src/main.rs` | Modify | Tick increment, command popup key handling, slash-command execution |
| `cli-tui/src/widgets/mod.rs` | Create | `LayoutMode` enum + module declarations |
| `cli-tui/src/widgets/header.rs` | Create | Top bar: brand · version · dir · model · status · tokens |
| `cli-tui/src/widgets/footer.rs` | Create | Bottom bar: status · spinner · hints · model |
| `cli-tui/src/widgets/transcript.rs` | Create | Chat messages (migrated from `ui.rs`) |
| `cli-tui/src/widgets/input.rs` | Create | Input box wrapper + `apply_style()` |
| `cli-tui/src/widgets/sidebar.rs` | Create | Tool call log (Wide mode only) |
| `cli-tui/src/widgets/command_popup.rs` | Create | Floating command menu triggered by `/` |

---

## Task 1: Extend App state

**Files:**
- Modify: `cli-tui/src/app.rs`
- Modify: `cli-tui/src/events.rs`

- [ ] **Step 1: Add `WsEvent::TokenUsage` to `events.rs`**

Replace the entire file:

```rust
use serde::Deserialize;
use serde_json::Value;

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WsEvent {
    Token { content: String },
    Thinking { content: String },
    ToolCall { tool: String, args: Value },
    Observation { #[allow(dead_code)] tool: String, result: Value },
    TokenUsage { input_tokens: u32, output_tokens: u32 },
    #[allow(dead_code)]
    Done,
    Error { message: String },
}
```

- [ ] **Step 2: Add new types to `app.rs`**

After the `ConnStatus` enum (around line 38), add:

```rust
// ── Command popup state ───────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct CommandPopupState {
    pub filter: String,
    pub selected: usize,
}

impl CommandPopupState {
    pub fn new() -> Self {
        Self { filter: String::new(), selected: 0 }
    }
}
```

- [ ] **Step 3: Add new `Action` variants**

In the `Action` enum (around line 66), add after `Quit`:

```rust
    Tick,
    PopupUp,
    PopupDown,
    PopupClose,
    CommandClear,
    CommandSetModel(String),
    CommandSetSystem(String),
    CommandHelp,
    CommandExport,
```

- [ ] **Step 4: Add new fields to `App` struct**

In the `App` struct (around line 83), add after `should_quit`:

```rust
    pub token_counts: (u32, u32),
    pub current_dir: String,
    pub tick: u64,
    pub command_popup: Option<CommandPopupState>,
```

- [ ] **Step 5: Initialise new fields in `App::new()`**

In the `Self { ... }` block of `App::new()`, add after `should_quit: false`:

```rust
            token_counts: (0, 0),
            current_dir: std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| "~".to_string()),
            tick: 0,
            command_popup: None,
```

- [ ] **Step 6: Handle new actions in `App::update()`**

In the `match action` block, add before the closing `}`:

```rust
            Action::Tick => self.tick = self.tick.wrapping_add(1),

            Action::PopupUp => {
                if let Some(ref mut p) = self.command_popup {
                    if p.selected > 0 { p.selected -= 1; }
                }
            }
            Action::PopupDown => {
                if let Some(ref mut p) = self.command_popup {
                    p.selected += 1;
                }
            }
            Action::PopupClose => self.command_popup = None,

            Action::CommandClear => {
                self.messages.clear();
                self.history.clear();
                self.scroll_offset = 0;
                self.command_popup = None;
            }
            Action::CommandSetModel(m) => {
                self.config.model = m;
                let _ = self.config.save();
                self.command_popup = None;
            }
            Action::CommandSetSystem(_s) => {
                // System prompt not persisted yet — future work
                self.command_popup = None;
            }
            Action::CommandHelp => {
                self.messages.push(ChatMessage::Assistant {
                    parts: vec![AssistantPart::Text(
                        "**Commands**\n\n\
                         `/model <name>` — 切换模型\n\
                         `/clear` — 清空会话\n\
                         `/system <text>` — 设置 system prompt\n\
                         `/help` — 显示此帮助\n\
                         `/export` — 导出会话为 JSON\n\n\
                         **Keys:** `↑/↓` scroll · `Ctrl+O` toggle thinking · `Ctrl+C` quit"
                        .to_string(),
                    )],
                    done: true,
                });
                self.command_popup = None;
            }
            Action::CommandExport => {
                let filename = format!(
                    "proteinclaw-session-{}.json",
                    std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_secs()
                );
                let _ = std::fs::write(&filename, serde_json::to_string_pretty(&self.history).unwrap_or_default());
                self.command_popup = None;
            }
```

- [ ] **Step 7: Handle `WsEvent::TokenUsage` in `handle_ws_event()`**

In the `match event` block of `handle_ws_event`, add before `WsEvent::Done =>`:

```rust
            WsEvent::TokenUsage { input_tokens, output_tokens } => {
                self.token_counts = (input_tokens, output_tokens);
            }
```

- [ ] **Step 8: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: `warning: ...` lines only, no `error` lines.

- [ ] **Step 9: Commit**

```bash
git add cli-tui/src/app.rs cli-tui/src/events.rs
git commit -m "feat(tui): extend App state for vtcode-style redesign"
```

---

## Task 2: Scaffold widget module

**Files:**
- Create: `cli-tui/src/widgets/mod.rs`
- Create stubs: `header.rs`, `footer.rs`, `transcript.rs`, `input.rs`, `sidebar.rs`, `command_popup.rs`

- [ ] **Step 1: Create `widgets/mod.rs`**

```rust
// cli-tui/src/widgets/mod.rs
pub mod command_popup;
pub mod footer;
pub mod header;
pub mod input;
pub mod sidebar;
pub mod transcript;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LayoutMode {
    Compact,
    Standard,
    Wide,
}

impl LayoutMode {
    pub fn from_width(w: u16) -> Self {
        if w < 80 { Self::Compact }
        else if w < 120 { Self::Standard }
        else { Self::Wide }
    }
}
```

- [ ] **Step 2: Create `widgets/header.rs` stub**

```rust
// cli-tui/src/widgets/header.rs
use ratatui::{Frame, layout::Rect};
use crate::app::App;

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let _ = (f, area, app);
}
```

- [ ] **Step 3: Create `widgets/footer.rs` stub**

```rust
// cli-tui/src/widgets/footer.rs
use ratatui::{Frame, layout::Rect};
use crate::app::App;

pub fn draw(f: &mut Frame, area: Rect, app: &App, textarea_nonempty: bool) {
    let _ = (f, area, app, textarea_nonempty);
}
```

- [ ] **Step 4: Create `widgets/transcript.rs` stub**

```rust
// cli-tui/src/widgets/transcript.rs
use ratatui::{Frame, layout::Rect};
use crate::app::App;

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let _ = (f, area, app);
}
```

- [ ] **Step 5: Create `widgets/input.rs` stub**

```rust
// cli-tui/src/widgets/input.rs
use ratatui::{Frame, layout::Rect, style::{Color, Style}, widgets::{Block, Borders}};
use tui_textarea::TextArea;

pub fn draw(f: &mut Frame, area: Rect, textarea: &TextArea) {
    let _ = (f, area, textarea);
}

pub fn apply_style(textarea: &mut TextArea) {
    textarea.set_block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::Rgb(0x00, 0xb0, 0xaa)))
            .title(" Message (Enter → send  Shift+Enter → newline  Ctrl+C → quit) "),
    );
    textarea.set_cursor_line_style(Style::default());
}
```

- [ ] **Step 6: Create `widgets/sidebar.rs` stub**

```rust
// cli-tui/src/widgets/sidebar.rs
use ratatui::{Frame, layout::Rect};
use crate::app::App;

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let _ = (f, area, app);
}
```

- [ ] **Step 7: Create `widgets/command_popup.rs` stub**

```rust
// cli-tui/src/widgets/command_popup.rs
use ratatui::{Frame, layout::Rect};
use crate::app::App;

pub fn draw(f: &mut Frame, input_area: Rect, app: &App) {
    let _ = (f, input_area, app);
}

/// Returns the list of commands filtered by `filter` (text after '/').
pub fn filtered_commands(filter: &str) -> Vec<(&'static str, &'static str)> {
    const COMMANDS: &[(&str, &str)] = &[
        ("/model ", "切换模型"),
        ("/clear", "清空会话历史"),
        ("/system ", "设置 system prompt"),
        ("/help", "显示全部命令"),
        ("/export", "导出会话为 JSON"),
    ];
    COMMANDS
        .iter()
        .filter(|(cmd, _)| cmd[1..].starts_with(filter))
        .copied()
        .collect()
}
```

- [ ] **Step 8: Register `widgets` module in `main.rs`**

In `cli-tui/src/main.rs`, add after the existing `mod` declarations at the top:

```rust
mod widgets;
```

- [ ] **Step 9: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
git add cli-tui/src/widgets/ cli-tui/src/main.rs
git commit -m "feat(tui): scaffold widgets module with stubs"
```

---

## Task 3: Header widget

**Files:**
- Modify: `cli-tui/src/widgets/header.rs`

- [ ] **Step 1: Implement `header.rs`**

Replace the entire stub with:

```rust
use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::Paragraph,
};
use crate::app::{App, ConnStatus};
use super::LayoutMode;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let mode = LayoutMode::from_width(area.width);

    let (conn_dot, conn_color) = match app.conn_status {
        ConnStatus::Connected    => ("●", Color::Green),
        ConnStatus::Connecting   => ("◌", Color::Yellow),
        ConnStatus::Disconnected => ("✗", Color::Red),
    };

    let line = match mode {
        LayoutMode::Compact => Line::from(vec![
            Span::styled(" ProteinClaw ", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD)),
            Span::styled(conn_dot, Style::default().fg(conn_color)),
            Span::raw(" "),
        ]),
        _ => {
            let dir = shorten_path(&app.current_dir);
            let (in_t, out_t) = app.token_counts;
            let tok = if in_t == 0 && out_t == 0 {
                "↑? ↓? tok".to_string()
            } else {
                format!("↑{} ↓{} tok", fmt_tok(in_t), fmt_tok(out_t))
            };
            let version = env!("CARGO_PKG_VERSION");
            let right = format!("{} connected  │  {}  ", conn_dot, tok);
            let left_plain = format!(
                " ProteinClaw v{}  │  {}  │  {}",
                version, dir, &app.config.model
            );
            let pad = area.width
                .saturating_sub(left_plain.len() as u16 + right.len() as u16);

            Line::from(vec![
                Span::raw(" "),
                Span::styled("ProteinClaw", Style::default().fg(ACCENT).add_modifier(Modifier::BOLD)),
                Span::styled(
                    format!(" v{}  │  {}  │  {}", version, dir, &app.config.model),
                    Style::default().fg(Color::DarkGray),
                ),
                Span::raw(" ".repeat(pad as usize)),
                Span::styled(right, Style::default().fg(conn_color)),
            ])
        }
    };

    f.render_widget(
        Paragraph::new(line).style(Style::default().bg(Color::Rgb(0x1a, 0x1a, 0x2a))),
        area,
    );
}

fn shorten_path(path: &str) -> String {
    let shortened = if let Some(home) = dirs::home_dir() {
        let h = home.to_string_lossy();
        if path.starts_with(h.as_ref()) {
            format!("~{}", &path[h.len()..])
        } else {
            path.to_string()
        }
    } else {
        path.to_string()
    };
    if shortened.len() > 35 {
        format!("…{}", &shortened[shortened.len().saturating_sub(32)..])
    } else {
        shortened
    }
}

fn fmt_tok(n: u32) -> String {
    if n >= 1000 { format!("{:.1}k", n as f32 / 1000.0) } else { n.to_string() }
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/widgets/header.rs
git commit -m "feat(tui): implement header widget"
```

---

## Task 4: Footer widget

**Files:**
- Modify: `cli-tui/src/widgets/footer.rs`

- [ ] **Step 1: Implement `footer.rs`**

Replace the entire stub with:

```rust
use ratatui::{
    Frame,
    layout::{Constraint, Layout, Rect},
    style::{Color, Style},
    text::{Line, Span},
    widgets::Paragraph,
};
use crate::app::{App, ChatMessage, ConnStatus};
use super::LayoutMode;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);
const SPINNER: &[char] = &['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

pub fn draw(f: &mut Frame, area: Rect, app: &App, textarea_nonempty: bool) {
    let mode = LayoutMode::from_width(area.width);

    let is_processing = matches!(
        app.messages.last(),
        Some(ChatMessage::Assistant { done: false, .. })
    );

    let (conn_dot, conn_color) = match app.conn_status {
        ConnStatus::Connected    => ("●", ACCENT),
        ConnStatus::Connecting   => ("◌", Color::Yellow),
        ConnStatus::Disconnected => ("✗", Color::Red),
    };

    let hints: &str = if is_processing {
        "ctrl+c stop"
    } else if textarea_nonempty {
        "Enter 发送 • ↑ 历史 • Esc 取消"
    } else {
        "? help • / command"
    };

    match mode {
        LayoutMode::Compact => {
            let line = Line::from(vec![
                Span::styled(format!(" {} ", conn_dot), Style::default().fg(conn_color)),
                Span::styled(hints, Style::default().fg(Color::DarkGray)),
            ]);
            f.render_widget(Paragraph::new(line), area);
        }
        _ => {
            let rows = Layout::vertical([
                Constraint::Length(1),
                Constraint::Length(1),
            ])
            .split(area);

            // Row 1: status + spinner left, model right
            let spinner = if is_processing {
                format!(" {}", SPINNER[(app.tick / 4) as usize % SPINNER.len()])
            } else {
                String::new()
            };
            let model = app.config.model.as_str();
            let right1 = format!("{} ", model);
            let left1 = format!(" {} connected{}", conn_dot, spinner);
            let pad1 = rows[0].width.saturating_sub(left1.len() as u16 + right1.len() as u16);

            let line1 = Line::from(vec![
                Span::raw(" "),
                Span::styled(conn_dot, Style::default().fg(conn_color)),
                Span::styled(
                    format!(" connected{}", spinner),
                    Style::default().fg(Color::DarkGray),
                ),
                Span::raw(" ".repeat(pad1 as usize)),
                Span::styled(right1, Style::default().fg(Color::DarkGray)),
            ]);

            // Row 2: centered hints
            let line2 = Line::from(Span::styled(
                format!(" {}", hints),
                Style::default().fg(Color::DarkGray),
            ));

            f.render_widget(Paragraph::new(line1), rows[0]);
            f.render_widget(Paragraph::new(line2), rows[1]);
        }
    }
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/widgets/footer.rs
git commit -m "feat(tui): implement footer widget with spinner and context hints"
```

---

## Task 5: Transcript widget

**Files:**
- Modify: `cli-tui/src/widgets/transcript.rs`

- [ ] **Step 1: Implement `transcript.rs`**

Replace the stub with the full implementation (migrated from `ui.rs` `draw_messages` + `render_markdown`):

```rust
use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Paragraph, Wrap},
};
use crate::app::{App, AssistantPart, ChatMessage};
use super::LayoutMode;

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let mode = LayoutMode::from_width(area.width);
    let width = area.width.saturating_sub(2) as usize;
    let mut all_lines: Vec<Line> = Vec::new();

    for msg in app.messages.iter() {
        match msg {
            ChatMessage::User(text) => {
                all_lines.push(Line::raw(""));
                all_lines.push(Line::from(vec![
                    Span::styled("> ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                    Span::styled(text.as_str(), Style::default().add_modifier(Modifier::BOLD)),
                ]));
                all_lines.push(Line::raw(""));
            }

            ChatMessage::Assistant { parts, done } => {
                for (pi, part) in parts.iter().enumerate() {
                    match part {
                        AssistantPart::Text(text) => {
                            let mut md = render_markdown(text, width);
                            if !*done && pi == parts.len() - 1 {
                                if let Some(last) = md.last_mut() {
                                    last.spans.push(Span::styled("█", Style::default().fg(Color::White)));
                                } else {
                                    md.push(Line::from(Span::styled("█", Style::default().fg(Color::White))));
                                }
                            }
                            all_lines.extend(md);
                        }
                        AssistantPart::Thinking { content, expanded } => {
                            if *expanded {
                                all_lines.push(Line::from(vec![
                                    Span::styled("∴ ", Style::default().fg(Color::Magenta)),
                                    Span::styled("Thinking  [ctrl+o to collapse]", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
                                ]));
                                for line in render_markdown(content, width) {
                                    all_lines.push(line.patch_style(Style::default().fg(Color::DarkGray)));
                                }
                            } else {
                                all_lines.push(Line::from(vec![
                                    Span::styled("∴ ", Style::default().fg(Color::Magenta)),
                                    Span::styled("Thinking…  (ctrl+o to expand)", Style::default().fg(Color::DarkGray)),
                                ]));
                            }
                            all_lines.push(Line::raw(""));
                        }
                        AssistantPart::ToolCall { tool, args, result, expanded } => {
                            let (status, status_color) = if result.is_some() {
                                ("⏺", Color::Green)
                            } else {
                                ("⟳", Color::Yellow)
                            };
                            all_lines.push(Line::from(vec![
                                Span::styled(status, Style::default().fg(status_color)),
                                Span::raw("  "),
                                Span::styled(tool.as_str(), Style::default().add_modifier(Modifier::BOLD)),
                                Span::styled("  [enter to toggle]", Style::default().fg(Color::DarkGray)),
                            ]));
                            if *expanded {
                                let args_str = serde_json::to_string_pretty(args).unwrap_or_else(|_| args.to_string());
                                for line in args_str.lines() {
                                    all_lines.push(Line::from(vec![
                                        Span::raw("    "),
                                        Span::styled(line.to_string(), Style::default().fg(Color::Cyan)),
                                    ]));
                                }
                                if let Some(res) = result {
                                    all_lines.push(Line::from(Span::styled("  → result:", Style::default().fg(Color::DarkGray))));
                                    for line in res.lines() {
                                        all_lines.push(Line::from(vec![
                                            Span::raw("    "),
                                            Span::styled(line.to_string(), Style::default().fg(Color::DarkGray)),
                                        ]));
                                    }
                                }
                            }
                            all_lines.push(Line::raw(""));
                        }
                    }
                }
                if parts.is_empty() && !*done {
                    all_lines.push(Line::from(Span::styled("█", Style::default().fg(Color::White))));
                }
            }

            ChatMessage::Error(msg) => {
                all_lines.push(Line::raw(""));
                all_lines.push(Line::from(Span::styled("✗ Error", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))));
                all_lines.push(Line::from(vec![
                    Span::raw("  "),
                    Span::styled(msg.as_str(), Style::default().fg(Color::Red)),
                ]));
                all_lines.push(Line::raw(""));
            }
        }
    }

    if app.messages.is_empty() {
        all_lines.push(Line::raw(""));
        all_lines.push(Line::from(Span::styled("  Welcome to ProteinClaw", Style::default().fg(Color::Rgb(0x00, 0xb0, 0xaa)).add_modifier(Modifier::BOLD))));
        all_lines.push(Line::raw(""));
        all_lines.push(Line::from(Span::styled("  Ask anything about proteins, sequences, structures, or databases.", Style::default().fg(Color::DarkGray))));
        all_lines.push(Line::raw(""));
        all_lines.push(Line::from(Span::styled("  Ctrl+C quit  •  Ctrl+O toggle thinking  •  ↑/↓ scroll  •  / commands", Style::default().fg(Color::DarkGray))));
    }

    let inner_height = area.height.saturating_sub(2) as usize;
    let total = all_lines.len();
    let max_offset = total.saturating_sub(inner_height);
    let offset = app.scroll_offset.min(max_offset);
    let scroll_from_top = total.saturating_sub(inner_height + offset);

    let block = match mode {
        LayoutMode::Compact => Block::default().borders(Borders::NONE),
        _ => Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::DarkGray))
            .title(Span::styled(" Transcript ", Style::default().fg(Color::DarkGray))),
    };

    let para = Paragraph::new(Text::from(all_lines))
        .block(block)
        .wrap(Wrap { trim: false })
        .scroll((scroll_from_top as u16, 0));

    f.render_widget(para, area);
}

pub fn render_markdown(text: &str, _width: usize) -> Vec<Line<'static>> {
    use pulldown_cmark::{Event, Options, Parser, Tag, TagEnd};

    let mut lines: Vec<Line<'static>> = Vec::new();
    let mut current: Vec<Span<'static>> = Vec::new();
    let mut bold = false;
    let mut italic = false;
    let mut in_code_block = false;
    let mut in_item = false;
    let mut heading_level: u32 = 0;

    macro_rules! flush {
        () => {
            if !current.is_empty() {
                lines.push(Line::from(std::mem::take(&mut current)));
            }
        };
    }

    macro_rules! push_span {
        ($s:expr) => {{
            let mut style = Style::default();
            if bold { style = style.add_modifier(Modifier::BOLD); }
            if italic { style = style.add_modifier(Modifier::ITALIC); }
            if heading_level > 0 {
                style = style.add_modifier(Modifier::BOLD).add_modifier(Modifier::UNDERLINED).fg(Color::White);
            }
            current.push(Span::styled($s.to_string(), style));
        }};
    }

    for event in Parser::new_ext(text, Options::all()) {
        match event {
            Event::Start(Tag::Heading { level, .. }) => { flush!(); heading_level = level as u32; }
            Event::End(TagEnd::Heading(_)) => { flush!(); lines.push(Line::raw("")); heading_level = 0; }
            Event::Start(Tag::Paragraph) => {}
            Event::End(TagEnd::Paragraph) => { flush!(); lines.push(Line::raw("")); }
            Event::Start(Tag::CodeBlock(_)) => { in_code_block = true; flush!(); }
            Event::End(TagEnd::CodeBlock) => { in_code_block = false; lines.push(Line::raw("")); }
            Event::Start(Tag::List(_)) => {}
            Event::End(TagEnd::List(_)) => { lines.push(Line::raw("")); }
            Event::Start(Tag::Item) => { in_item = true; current.push(Span::raw("  • ")); }
            Event::End(TagEnd::Item) => { in_item = false; flush!(); }
            Event::Start(Tag::BlockQuote(_)) => { current.push(Span::styled("▏ ", Style::default().fg(Color::DarkGray))); }
            Event::End(TagEnd::BlockQuote(_)) => { flush!(); }
            Event::Start(Tag::Strong) => bold = true,
            Event::End(TagEnd::Strong) => bold = false,
            Event::Start(Tag::Emphasis) => italic = true,
            Event::End(TagEnd::Emphasis) => italic = false,
            Event::Start(Tag::Link { .. }) | Event::End(TagEnd::Link) => {}
            Event::Text(t) => {
                if in_code_block {
                    for line in t.lines() {
                        lines.push(Line::from(vec![
                            Span::styled("  ", Style::default().bg(Color::DarkGray)),
                            Span::styled(line.to_string(), Style::default().fg(Color::Cyan).bg(Color::DarkGray)),
                            Span::styled("  ", Style::default().bg(Color::DarkGray)),
                        ]));
                    }
                } else {
                    push_span!(t);
                }
            }
            Event::Code(c) => { current.push(Span::styled(c.to_string(), Style::default().fg(Color::Cyan))); }
            Event::SoftBreak => { current.push(Span::raw(" ")); }
            Event::HardBreak => { flush!(); }
            Event::Rule => {
                flush!();
                lines.push(Line::from(Span::styled("─".repeat(40), Style::default().fg(Color::DarkGray))));
            }
            _ => {}
        }
        let _ = in_item;
    }
    flush!();
    lines
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/widgets/transcript.rs
git commit -m "feat(tui): implement transcript widget (migrated from ui.rs)"
```

---

## Task 6: Input widget

**Files:**
- Modify: `cli-tui/src/widgets/input.rs`

- [ ] **Step 1: Implement `input.rs`**

Replace the stub with:

```rust
use ratatui::{Frame, layout::Rect, style::{Color, Modifier, Style}, widgets::{Block, Borders}};
use tui_textarea::TextArea;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

pub fn draw(f: &mut Frame, area: Rect, textarea: &TextArea) {
    f.render_widget(textarea, area);
}

/// Call this once after constructing the textarea, and again after content changes.
/// Always renders with accent border (input is the permanent focus area).
pub fn apply_style(textarea: &mut TextArea) {
    textarea.set_block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT).add_modifier(Modifier::BOLD))
            .title(Span::raw(" Message (Enter → send  Shift+Enter → newline  Ctrl+C → quit) ")),
    );
    textarea.set_cursor_line_style(Style::default());
}
```

Note: `Span` is needed for the title. Add the import at the top:

```rust
use ratatui::{Frame, layout::Rect, style::{Color, Modifier, Style}, text::Span, widgets::{Block, Borders}};
use tui_textarea::TextArea;
```

Full file:

```rust
use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::Span,
    widgets::{Block, Borders},
};
use tui_textarea::TextArea;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

pub fn draw(f: &mut Frame, area: Rect, textarea: &TextArea) {
    f.render_widget(textarea, area);
}

pub fn apply_style(textarea: &mut TextArea) {
    textarea.set_block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(ACCENT).add_modifier(Modifier::BOLD))
            .title(Span::raw(" Message (Enter → send  Shift+Enter → newline  Ctrl+C → quit) ")),
    );
    textarea.set_cursor_line_style(Style::default());
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/widgets/input.rs
git commit -m "feat(tui): implement input widget"
```

---

## Task 7: Sidebar widget

**Files:**
- Modify: `cli-tui/src/widgets/sidebar.rs`

- [ ] **Step 1: Implement `sidebar.rs`**

Replace the stub with:

```rust
use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Paragraph, Wrap},
};
use crate::app::{App, AssistantPart, ChatMessage};

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let mut lines: Vec<Line> = Vec::new();

    for msg in app.messages.iter() {
        if let ChatMessage::Assistant { parts, .. } = msg {
            for part in parts.iter() {
                if let AssistantPart::ToolCall { tool, args, result, .. } = part {
                    let (status, color) = if result.is_some() {
                        ("⏺", Color::Green)
                    } else {
                        ("⟳", Color::Yellow)
                    };
                    lines.push(Line::from(vec![
                        Span::styled(status, Style::default().fg(color)),
                        Span::raw(" "),
                        Span::styled(tool.as_str(), Style::default().add_modifier(Modifier::BOLD)),
                    ]));

                    // Show first arg key=value, truncated to fit sidebar
                    if let Some(obj) = args.as_object() {
                        if let Some((k, v)) = obj.iter().next() {
                            let val = v.as_str().unwrap_or(&v.to_string()).to_string();
                            let val = if val.len() > 18 { format!("{}…", &val[..15]) } else { val };
                            lines.push(Line::from(Span::styled(
                                format!("  {}={}", k, val),
                                Style::default().fg(Color::DarkGray),
                            )));
                        }
                    }

                    // Show result summary
                    if let Some(res) = result {
                        let summary = res.lines().next().unwrap_or("").trim();
                        let summary = if summary.len() > 20 { format!("{}…", &summary[..17]) } else { summary.to_string() };
                        lines.push(Line::from(Span::styled(
                            format!("  → {}", summary),
                            Style::default().fg(Color::DarkGray),
                        )));
                    }

                    lines.push(Line::raw(""));
                }
            }
        }
    }

    if lines.is_empty() {
        lines.push(Line::raw(""));
        lines.push(Line::from(Span::styled(
            " No tool calls yet",
            Style::default().fg(Color::DarkGray),
        )));
    }

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(" Tool Calls ", Style::default().fg(Color::DarkGray)));

    let para = Paragraph::new(Text::from(lines))
        .block(block)
        .wrap(Wrap { trim: true });

    f.render_widget(para, area);
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/widgets/sidebar.rs
git commit -m "feat(tui): implement sidebar widget (tool call log)"
```

---

## Task 8: Command Popup widget

**Files:**
- Modify: `cli-tui/src/widgets/command_popup.rs`

- [ ] **Step 1: Implement `command_popup.rs`**

Replace the stub with:

```rust
use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Clear, Paragraph},
};
use crate::app::App;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

/// Returns commands whose name (after `/`) starts with `filter`.
pub fn filtered_commands(filter: &str) -> Vec<(&'static str, &'static str)> {
    const COMMANDS: &[(&str, &str)] = &[
        ("/model ", "切换模型"),
        ("/clear", "清空会话历史"),
        ("/system ", "设置 system prompt"),
        ("/help", "显示全部命令"),
        ("/export", "导出会话为 JSON"),
    ];
    COMMANDS
        .iter()
        .filter(|(cmd, _)| {
            let name = &cmd[1..]; // strip leading '/'
            name.starts_with(filter) || filter.is_empty()
        })
        .copied()
        .collect()
}

pub fn draw(f: &mut Frame, input_area: Rect, app: &App) {
    let popup_state = match &app.command_popup {
        Some(s) => s,
        None => return,
    };

    let cmds = filtered_commands(&popup_state.filter);
    if cmds.is_empty() {
        return;
    }

    // Clamp selected index
    let selected = popup_state.selected.min(cmds.len().saturating_sub(1));

    let popup_height = (cmds.len() as u16 + 2).min(8);
    // Place popup directly above the input area
    let y = input_area.y.saturating_sub(popup_height);
    let popup_area = Rect {
        x: input_area.x,
        y,
        width: input_area.width,
        height: popup_height,
    };

    f.render_widget(Clear, popup_area);

    let lines: Vec<Line> = cmds
        .iter()
        .enumerate()
        .map(|(i, (cmd, desc))| {
            if i == selected {
                Line::from(vec![
                    Span::styled(
                        format!(" {} ", cmd),
                        Style::default().fg(Color::Black).bg(ACCENT).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(
                        format!(" {}", desc),
                        Style::default().fg(Color::Black).bg(ACCENT),
                    ),
                ])
            } else {
                Line::from(vec![
                    Span::styled(format!(" {} ", cmd), Style::default().fg(ACCENT)),
                    Span::styled(format!(" {}", desc), Style::default().fg(Color::DarkGray)),
                ])
            }
        })
        .collect();

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(ACCENT))
        .title(Span::styled(" Commands ", Style::default().fg(ACCENT)));

    f.render_widget(Paragraph::new(Text::from(lines)).block(block), popup_area);
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/widgets/command_popup.rs
git commit -m "feat(tui): implement command popup widget"
```

---

## Task 9: Rewrite `ui.rs` as layout orchestrator

**Files:**
- Modify: `cli-tui/src/ui.rs`

- [ ] **Step 1: Replace `ui.rs` entirely**

```rust
use ratatui::{
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Wrap},
    Frame,
};
use tui_textarea::TextArea;

use crate::app::{App, AssistantPart, ChatMessage, ConnStatus, Screen, SetupState};
use crate::widgets::{self, LayoutMode};

// ── Public entry point ───────────────────────────────────────────────────────

pub fn draw(f: &mut Frame, app: &App, textarea: &TextArea) {
    match &app.screen {
        Screen::Setup(st) => draw_setup(f, st),
        Screen::Chat => draw_chat(f, app, textarea),
    }
}

// ── Chat view ────────────────────────────────────────────────────────────────

fn draw_chat(f: &mut Frame, app: &App, textarea: &TextArea) {
    let area = f.area();
    let mode = LayoutMode::from_width(area.width);

    let input_height = (textarea.lines().len() as u16 + 2).clamp(3, 8);
    let footer_height: u16 = match mode {
        LayoutMode::Compact => 1,
        _ => 2,
    };

    let chunks = Layout::vertical([
        Constraint::Length(1),             // header
        Constraint::Min(0),                // main (transcript [+ sidebar])
        Constraint::Length(input_height),  // input
        Constraint::Length(footer_height), // footer
    ])
    .split(area);

    widgets::header::draw(f, chunks[0], app);

    match mode {
        LayoutMode::Wide => {
            let sidebar_width = (area.width * 30 / 100).max(24);
            let cols = Layout::horizontal([
                Constraint::Min(0),
                Constraint::Length(sidebar_width),
            ])
            .split(chunks[1]);
            widgets::transcript::draw(f, cols[0], app);
            widgets::sidebar::draw(f, cols[1], app);
        }
        _ => {
            widgets::transcript::draw(f, chunks[1], app);
        }
    }

    widgets::input::draw(f, chunks[2], textarea);
    widgets::footer::draw(f, chunks[3], app, !textarea.is_empty());

    if app.command_popup.is_some() {
        widgets::command_popup::draw(f, chunks[2], app);
    }
}

// ── Setup wizard (unchanged) ─────────────────────────────────────────────────

fn draw_setup(f: &mut Frame, st: &SetupState) {
    let area = f.area();
    let vpad = area.height.saturating_sub(18) / 2;
    let hpad = area.width.saturating_sub(60) / 2;
    let popup = Rect {
        x: hpad,
        y: vpad,
        width: area.width.min(60),
        height: area.height.min(18),
    };

    f.render_widget(Clear, popup);

    let block = Block::default()
        .title(" ProteinClaw — First-run Setup ")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::Cyan));
    f.render_widget(block, popup);

    let inner = Rect {
        x: popup.x + 1,
        y: popup.y + 1,
        width: popup.width.saturating_sub(2),
        height: popup.height.saturating_sub(2),
    };

    let mut lines: Vec<Line> = vec![
        Line::from(Span::styled(
            "No API key found in the environment.",
            Style::default().fg(Color::Yellow),
        )),
        Line::raw(""),
        Line::from(Span::raw("Set one of these before launching ProteinClaw:")),
        Line::raw("  ANTHROPIC_API_KEY"),
        Line::raw("  OPENAI_API_KEY"),
        Line::raw("  DEEPSEEK_API_KEY"),
        Line::raw("  MINIMAX_API_KEY"),
        Line::raw(""),
        Line::from(vec![
            Span::raw("Model: "),
            Span::styled(&st.model_buf, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("_", Style::default().fg(Color::Green).add_modifier(Modifier::SLOW_BLINK)),
        ]),
        Line::raw(""),
        Line::from(vec![
            Span::styled("[Enter] ", Style::default().fg(Color::Cyan)),
            Span::raw("save and continue   "),
            Span::styled("[Backspace] ", Style::default().fg(Color::Cyan)),
            Span::raw("delete"),
        ]),
    ];

    if let Some(err) = &st.error {
        lines.push(Line::raw(""));
        lines.push(Line::from(Span::styled(err.as_str(), Style::default().fg(Color::Red))));
    }

    f.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), inner);
}
```

- [ ] **Step 2: Verify compilation**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo check 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/ui.rs
git commit -m "feat(tui): rewrite ui.rs as layout orchestrator (3 layout modes)"
```

---

## Task 10: Update `main.rs` — tick, popup keys, slash-command execution

**Files:**
- Modify: `cli-tui/src/main.rs`

- [ ] **Step 1: Add `mod widgets` and import `apply_style`**

At the top of `main.rs`, the `mod widgets;` declaration was already added in Task 2, Step 8. Update the initial textarea styling to use `widgets::input::apply_style`. Replace the `style_textarea` call and function:

Find and replace the initial textarea setup block (around line 44):
```rust
    style_textarea(&mut textarea, false);
```
Change to:
```rust
    widgets::input::apply_style(&mut textarea);
```

- [ ] **Step 2: Add tick dispatch in the event loop**

After the `while let Ok(ev) = event_rx.try_recv()` block (around line 62), add:

```rust
        app.update(Action::Tick);
```

This should be placed just before the `if event::poll(tick)?` line.

- [ ] **Step 3: Add popup key handling in `handle_chat_key`**

In `handle_chat_key`, add a popup guard at the very top of the function body, before the scroll match:

```rust
fn handle_chat_key(
    key: event::KeyEvent,
    app: &mut App,
    textarea: &mut TextArea,
    cmd_tx: &mpsc::UnboundedSender<WsCmd>,
) {
    use crate::widgets::command_popup::filtered_commands;

    // ── Command popup navigation ─────────────────────────────────────────────
    if app.command_popup.is_some() {
        match (key.modifiers, key.code) {
            (KeyModifiers::NONE, KeyCode::Esc) => {
                app.update(Action::PopupClose);
                return;
            }
            (KeyModifiers::NONE, KeyCode::Up) => {
                app.update(Action::PopupUp);
                return;
            }
            (KeyModifiers::NONE, KeyCode::Down) => {
                app.update(Action::PopupDown);
                return;
            }
            (KeyModifiers::NONE, KeyCode::Enter) => {
                // Fill selected command into textarea
                if let Some(ref popup) = app.command_popup {
                    let cmds = filtered_commands(&popup.filter);
                    let idx = popup.selected.min(cmds.len().saturating_sub(1));
                    if let Some((cmd, _)) = cmds.get(idx) {
                        *textarea = TextArea::default();
                        textarea.set_placeholder_text(
                            "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
                        );
                        widgets::input::apply_style(textarea);
                        // Insert command text (move cursor to end)
                        for ch in cmd.chars() {
                            textarea.insert_char(ch);
                        }
                    }
                }
                app.update(Action::PopupClose);
                return;
            }
            _ => {}
        }
    }
```

Keep the rest of `handle_chat_key` unchanged below this block.

- [ ] **Step 4: Replace textarea forwarding + popup sync**

Replace the last section of `handle_chat_key` (the "All other keys → forward to textarea" part):

```rust
    // All other keys → forward to textarea
    textarea.input(key);
    widgets::input::apply_style(textarea);

    // Sync command popup with current input
    let first_line = textarea.lines().first().map(|s| s.as_str()).unwrap_or("").to_string();
    if first_line.starts_with('/') {
        let filter = first_line[1..].to_string();
        match app.command_popup {
            None => {
                app.command_popup = Some(crate::app::CommandPopupState { filter, selected: 0 });
            }
            Some(ref mut p) => {
                p.filter = filter;
                let max = crate::widgets::command_popup::filtered_commands(&p.filter)
                    .len()
                    .saturating_sub(1);
                p.selected = p.selected.min(max);
            }
        }
    } else {
        app.command_popup = None;
    }
```

- [ ] **Step 5: Handle slash-command execution on Enter**

In `handle_chat_key`, the Enter handler currently sends any non-empty text to WS. Update it to check for slash commands first. Replace the Enter block:

```rust
    // Enter → execute command or send message
    if key.modifiers == KeyModifiers::NONE && key.code == KeyCode::Enter {
        let text: String = textarea.lines().join("\n").trim().to_string();
        if !text.is_empty() {
            // Reset textarea
            *textarea = TextArea::default();
            textarea.set_placeholder_text(
                "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
            );
            widgets::input::apply_style(textarea);
            app.command_popup = None;

            // Parse slash commands
            if text.starts_with('/') {
                let (cmd, rest) = text.split_once(' ').unwrap_or((&text, ""));
                match cmd {
                    "/clear"  => { app.update(Action::CommandClear); }
                    "/help"   => { app.update(Action::CommandHelp); }
                    "/export" => { app.update(Action::CommandExport); }
                    "/model"  => {
                        let model = rest.trim().to_string();
                        if !model.is_empty() {
                            app.update(Action::CommandSetModel(model));
                        }
                    }
                    "/system" => {
                        let sys = rest.trim().to_string();
                        if !sys.is_empty() {
                            app.update(Action::CommandSetSystem(sys));
                        }
                    }
                    _ => {
                        app.messages.push(crate::app::ChatMessage::Error(
                            format!("Unknown command: {}. Type /help for a list.", cmd),
                        ));
                    }
                }
                return;
            }

            // Normal message → send to WS
            let history = app.history.clone();
            let model = app.config.model.clone();
            let _ = ws::send_message(cmd_tx, text.clone(), history, model);
            app.update(Action::SendMessage(text));
        }
        return;
    }
```

- [ ] **Step 6: Remove old `style_textarea` function**

Delete the `style_textarea` function at the bottom of `main.rs` (it is now replaced by `widgets::input::apply_style`).

- [ ] **Step 7: Verify full build**

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo build 2>&1 | tail -20
```

Expected: `Compiling proteinclaw-tui ...` then `Finished`. Fix any remaining errors before committing.

- [ ] **Step 8: Commit**

```bash
git add cli-tui/src/main.rs
git commit -m "feat(tui): update main.rs — tick, popup navigation, slash-command execution"
```

---

## Task 11: Visual smoke-test

- [ ] **Step 1: Run the TUI**

```bash
cd /mnt/d/data/code/ProteinClaw && bash scripts/tui.sh
```

Or directly:

```bash
cd /mnt/d/data/code/ProteinClaw/cli-tui && cargo run
```

- [ ] **Step 2: Verify Standard mode (80–119 cols)**
  - Header shows: `ProteinClaw vX.X  │  <dir>  │  <model>` left, `● connected │ ↑? ↓? tok` right
  - Transcript panel has dimmed border with `Transcript` title
  - Input box has accent (`#00b0aa`) bold border
  - Footer row 1: `● connected` left, model right; row 2: `? help • / command`

- [ ] **Step 3: Verify command popup**
  - Type `/` — popup appears above input with all 5 commands
  - Type `/m` — popup filters to `/model` only
  - Press `↓`/`↑` — selection highlight moves
  - Press `Enter` — `/model ` is filled into input, popup closes
  - Press `Esc` — popup closes, input unchanged

- [ ] **Step 4: Verify `/clear`**
  - Send a message, then type `/clear` and press `Enter`
  - Chat history clears, welcome screen returns

- [ ] **Step 5: Verify layout mode transitions**
  - Resize terminal below 80 cols → Compact mode (no borders, minimal header)
  - Resize to 120+ cols → Wide mode (Tool Calls sidebar appears on right)

- [ ] **Step 6: Final commit if any fixes were needed**

```bash
git add -p
git commit -m "fix(tui): visual smoke-test fixes"
```
