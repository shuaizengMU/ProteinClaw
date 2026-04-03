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
