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
