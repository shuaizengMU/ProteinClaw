use ratatui::{
    Frame,
    layout::{Constraint, Layout, Rect},
    style::{Color, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
};
use tui_textarea::TextArea;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

pub fn draw(f: &mut Frame, area: Rect, textarea: &TextArea) {
    // Top border line
    let rows = Layout::vertical([
        Constraint::Length(1),           // top border
        Constraint::Min(1),              // prompt + textarea
        Constraint::Length(1),           // bottom border
    ]).split(area);

    let border_line = "─".repeat(area.width as usize);
    f.render_widget(
        Paragraph::new(Line::from(Span::styled(&border_line, Style::default().fg(ACCENT)))),
        rows[0],
    );
    f.render_widget(
        Paragraph::new(Line::from(Span::styled(&border_line, Style::default().fg(ACCENT)))),
        rows[2],
    );

    // Prompt symbol + textarea
    let cols = Layout::horizontal([
        Constraint::Length(2),           // ❯ symbol
        Constraint::Min(1),              // textarea
    ]).split(rows[1]);

    f.render_widget(
        Paragraph::new(Line::from(Span::styled("❯ ", Style::default().fg(ACCENT)))),
        cols[0],
    );
    f.render_widget(textarea, cols[1]);
}

pub fn apply_style(textarea: &mut TextArea) {
    textarea.set_block(Block::default().borders(Borders::NONE));
    textarea.set_cursor_line_style(Style::default());
}
