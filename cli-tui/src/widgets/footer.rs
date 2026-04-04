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

    let ctrl_c_pending = app.ctrl_c_at
        .map(|t| t.elapsed().as_secs() < 2)
        .unwrap_or(false);

    let hints: &str = if ctrl_c_pending {
        "Press Ctrl+C again to quit"
    } else if is_processing {
        "ctrl+c stop"
    } else if textarea_nonempty {
        "Enter send • ↑ history • Esc cancel"
    } else {
        "? help • / command"
    };

    let hint_color = if ctrl_c_pending { Color::Yellow } else { Color::DarkGray };

    match mode {
        LayoutMode::Compact => {
            let line = Line::from(vec![
                Span::styled(format!(" {} ", conn_dot), Style::default().fg(conn_color)),
                Span::styled(hints, Style::default().fg(hint_color)),
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

            // Row 2: hints
            let line2 = Line::from(Span::styled(
                format!(" {}", hints),
                Style::default().fg(hint_color),
            ));

            f.render_widget(Paragraph::new(line1), rows[0]);
            f.render_widget(Paragraph::new(line2), rows[1]);
        }
    }
}
