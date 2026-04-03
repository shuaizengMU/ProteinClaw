# Welcome Screen Redesign — Design Spec

## Goal

Replace the plain-text welcome screen with a visually rich splash page inspired by the Claude Code welcome screen: a large braille art logo followed by a "Did you know?" tip box showing keyboard shortcuts.

## Layout

Rendered in the transcript area when `app.messages.is_empty()`. Top-to-bottom:

1. Vertical padding — blank lines to push content toward vertical center
2. Braille art logo — "ProteinClaw" in Unicode braille characters, ~9 rows tall, left-aligned
3. One blank line
4. "Did you know?" rounded border box — one static keyboard-shortcut tip
5. Nothing below the box (footer already shows shortcut hints)

## Visual Design

### Logo

"ProteinClaw" rendered in Unicode braille dot art, ~9 rows × ~80 columns. Stored as `const LOGO: &[&str]` — a slice of string literals, one per row. Color: teal `Color::Rgb(0x00, 0xb0, 0xaa)` (existing accent color).

### Did you know? box

Ratatui `Block` with `Borders::ALL`, `BorderType::Rounded`, title `" Did you know? "` in `DarkGray`. Inner content:

```
╭─── Did you know? ──────────────────────────────╮
│                                                 │
│  /model <name>  switch model for this session   │
│  Ctrl+O         toggle thinking blocks          │
│  ↑ / ↓          scroll  •  Ctrl+C  quit         │
│                                                 │
╰─────────────────────────────────────────────────╯
```

- Box border: `Color::DarkGray`
- Shortcut keys (e.g. `/model <name>`, `Ctrl+O`): `Color::White`
- Descriptions: `Color::DarkGray`
- Box left-indented 2 spaces; width follows logo width

## Architecture

### Files

| Action | Path |
|--------|------|
| Create | `cli-tui/src/widgets/welcome.rs` |
| Modify | `cli-tui/src/widgets/mod.rs` |
| Modify | `cli-tui/src/widgets/transcript.rs` |

### `welcome.rs`

```rust
pub fn draw(f: &mut Frame, area: Rect) { ... }
```

- `const LOGO: &[&str]` — braille art rows
- Computes vertical padding as `(area.height.saturating_sub(logo_rows + tip_box_height)) / 2`
- Renders each logo row as a `Line` of teal `Span`
- Renders tip box as a `Paragraph` inside a rounded `Block`

### `mod.rs`

Add `pub mod welcome;`.

### `transcript.rs`

Replace:
```rust
if app.messages.is_empty() {
    // current inline welcome lines
}
```
with:
```rust
if app.messages.is_empty() {
    super::welcome::draw(f, area);
    return;
}
```

### No state changes

`App` and `app.rs` are not modified. The welcome screen is purely a render-time decision based on `app.messages.is_empty()`.
