# Welcome Screen Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain welcome screen with a braille art logo + "Did you know?" tip box, matching the Claude Code aesthetic.

**Architecture:** Extract welcome screen rendering to a new `widgets/welcome.rs` module. `transcript.rs` calls `welcome::draw()` when messages are empty. No state changes — purely a render-time decision.

**Tech Stack:** Rust, ratatui 0.29, crossterm

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Create | `cli-tui/src/widgets/welcome.rs` | All welcome screen rendering: logo + tip box |
| Modify | `cli-tui/src/widgets/mod.rs` | Register `welcome` module |
| Modify | `cli-tui/src/widgets/transcript.rs` | Delegate to `welcome::draw()` when empty |

---

### Task 1: Create `welcome.rs` with logo and tip box

**Files:**
- Create: `cli-tui/src/widgets/welcome.rs`

- [ ] **Step 1: Create `cli-tui/src/widgets/welcome.rs`**

Write the full file:

```rust
use ratatui::{
    Frame,
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders, Paragraph},
};

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

const LOGO: &[&str] = &[
    "⣿⠛⠛⠛⢻⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠛⠛⠛⢻⡇⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    "⣿⠀⠀⠀⢸⡇⠀⣤⣤⣤⣤⣤⡄⠀⣤⣤⣤⣤⣤⡄⠀⣤⣤⣿⣤⣤⣤⠀⣤⣤⣤⣤⣤⡄⠀⠀⣤⣤⠀⠀⠀⠀⣤⣤⣤⣤⣤⡄⠀⣿⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⢠⣤⣤⣤⣤⡄⠀⣤⠀⣤⠀⢠⡄⠀",
    "⣿⠛⠛⠛⠻⠇⠀⣿⠀⠀⠀⢸⡇⠀⣿⠀⠀⠀⢸⡇⠀⠀⠀⣿⠀⠀⠀⠀⣿⣤⣤⣤⣼⡇⠀⠀⣿⣿⠀⠀⠀⠀⣿⠛⠛⠛⢻⡇⠀⣿⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⣤⣤⣤⣤⣼⡇⠀⣿⠀⣿⠀⢸⡇⠀",
    "⣿⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⢸⡇⠀⠀⠀⣿⣤⣤⡄⠀⣿⠀⠀⠀⠀⠀⠀⠀⣿⣿⠀⠀⠀⠀⣿⠀⠀⠀⢸⡇⠀⣿⠀⠀⠀⢀⡀⠀⠀⣿⣤⣤⣤⡄⠀⣿⠀⠀⠀⢸⡇⠀⣿⠶⣿⠶⢾⡇⠀",
    "⠿⠀⠀⠀⠀⠀⠀⠿⠀⠀⠀⠀⠀⠀⠛⠛⠛⠛⠛⠃⠀⠀⠀⠿⠿⠿⠇⠀⠛⠛⠛⠛⠛⠀⠀⠀⠿⠿⠀⠀⠀⠀⠿⠀⠀⠀⠸⠇⠀⣿⣤⣤⣤⣼⡇⠀⠀⠿⠿⠿⠿⠇⠀⠛⠛⠛⠛⠛⠃⠀⠿⠀⠿⠀⠸⠇⠀",
];

const TIP_LINES: &[(&str, &str)] = &[
    ("/model <name>", "switch model for this session"),
    ("Ctrl+O",        "toggle thinking blocks"),
    ("↑ / ↓",         "scroll  •  Ctrl+C  quit"),
    ("/clear",        "clear conversation history"),
];

pub fn draw(f: &mut Frame, area: Rect) {
    // Compute how tall the content block is:
    //   logo rows + 1 blank + tip box (2 border + 1 blank + tips + 1 blank)
    let logo_rows = LOGO.len() as u16;
    let tip_inner = TIP_LINES.len() as u16 + 2; // padding lines inside box
    let tip_box_height = tip_inner + 2; // top + bottom border
    let content_height = logo_rows + 1 + tip_box_height;

    // Vertical centering: push content toward the middle
    let top_pad = area.height.saturating_sub(content_height) / 2;
    let chunks = Layout::vertical([
        Constraint::Length(top_pad),
        Constraint::Length(logo_rows),
        Constraint::Length(1), // blank
        Constraint::Length(tip_box_height),
        Constraint::Min(0),
    ])
    .split(area);

    // ── Logo ─────────────────────────────────────────────────────────────────
    let logo_lines: Vec<Line> = LOGO
        .iter()
        .map(|row| Line::from(Span::styled(*row, Style::default().fg(ACCENT))))
        .collect();
    f.render_widget(
        Paragraph::new(logo_lines),
        chunks[1],
    );

    // ── Tip box ───────────────────────────────────────────────────────────────
    let tip_box_width = 52u16;
    let tip_area = {
        let mut a = chunks[3];
        a.width = a.width.min(tip_box_width);
        a
    };

    let mut inner_lines: Vec<Line> = vec![Line::raw("")];
    for (key, desc) in TIP_LINES {
        inner_lines.push(Line::from(vec![
            Span::raw("  "),
            Span::styled(
                format!("{:<16}", key),
                Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
            ),
            Span::styled(*desc, Style::default().fg(Color::DarkGray)),
        ]));
    }
    inner_lines.push(Line::raw(""));

    let block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(
            " Did you know? ",
            Style::default().fg(Color::DarkGray),
        ));

    f.render_widget(
        Paragraph::new(inner_lines).block(block),
        tip_area,
    );
}
```

- [ ] **Step 2: Verify file saved correctly**

```bash
wc -l cli-tui/src/widgets/welcome.rs
```

Expected: ~70 lines.

---

### Task 2: Register the module and wire up `transcript.rs`

**Files:**
- Modify: `cli-tui/src/widgets/mod.rs:1`
- Modify: `cli-tui/src/widgets/transcript.rs:137-144`

- [ ] **Step 1: Add `pub mod welcome;` to `mod.rs`**

In `cli-tui/src/widgets/mod.rs`, add one line after line 6 (`pub mod transcript;`):

```rust
pub mod welcome;
```

Full file after edit:

```rust
pub mod command_popup;
pub mod footer;
pub mod header;
pub mod input;
pub mod sidebar;
pub mod transcript;
pub mod welcome;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LayoutMode {
    Compact,
    Standard,
    Wide,
}

impl LayoutMode {
    pub fn from_width(w: u16) -> Self {
        if w < 80 {
            Self::Compact
        } else if w < 120 {
            Self::Standard
        } else {
            Self::Wide
        }
    }
}
```

- [ ] **Step 2: Replace inline welcome block in `transcript.rs`**

In `cli-tui/src/widgets/transcript.rs`, find lines 137–144 (the `if app.messages.is_empty()` block):

```rust
    if app.messages.is_empty() {
        all_lines.push(Line::raw(""));
        all_lines.push(Line::from(Span::styled("  Welcome to ProteinClaw", Style::default().fg(Color::Rgb(0x00, 0xb0, 0xaa)).add_modifier(Modifier::BOLD))));
        all_lines.push(Line::raw(""));
        all_lines.push(Line::from(Span::styled("  Ask anything about proteins, sequences, structures, or databases.", Style::default().fg(Color::DarkGray))));
        all_lines.push(Line::raw(""));
        all_lines.push(Line::from(Span::styled("  Ctrl+C quit  •  Ctrl+O toggle thinking  •  ↑/↓ scroll  •  / commands", Style::default().fg(Color::DarkGray))));
    }
```

Replace with:

```rust
    if app.messages.is_empty() {
        super::welcome::draw(f, area);
        return;
    }
```

The `return` is required because `f` is borrowed by `welcome::draw` and must not be used again for the `Paragraph` widget below.

- [ ] **Step 3: Compile**

```bash
cargo check -p cli-tui
```

Expected: `Finished` with at most pre-existing dead-code warnings. Fix any errors before proceeding.

- [ ] **Step 4: Commit**

```bash
git add cli-tui/src/widgets/welcome.rs cli-tui/src/widgets/mod.rs cli-tui/src/widgets/transcript.rs
git commit -m "feat(tui): redesign welcome screen with braille art logo and tip box"
```

---

### Task 3: Smoke-test the welcome screen visually

- [ ] **Step 1: Run the TUI and verify the welcome screen renders**

```bash
cargo run -p cli-tui
```

Check:
- The teal braille logo appears near the top-center of the transcript area
- A rounded `╭─ Did you know? ─╮` box appears below the logo
- The four shortcut rows are inside the box with keys in white and descriptions in gray
- Once a message is sent, the welcome screen disappears and the transcript renders normally

- [ ] **Step 2: Verify on narrow terminal (< 80 cols)**

Resize the terminal to ~60 columns and relaunch. The logo will overflow horizontally (expected — braille art is 77 chars wide) but the rest of the UI must not crash or panic.

- [ ] **Step 3: If logo clips badly on narrow terminals, add a guard**

In `welcome.rs`, wrap the logo rendering in a width check:

```rust
    // Only draw logo if terminal is wide enough
    if area.width >= 78 {
        let logo_lines: Vec<Line> = LOGO
            .iter()
            .map(|row| Line::from(Span::styled(*row, Style::default().fg(ACCENT))))
            .collect();
        f.render_widget(Paragraph::new(logo_lines), chunks[1]);
    }
```

Re-run `cargo check -p cli-tui` after this change.
