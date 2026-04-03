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
        let char_count = shortened.chars().count();
        let start = shortened
            .char_indices()
            .nth(char_count.saturating_sub(32))
            .map(|(i, _)| i)
            .unwrap_or(0);
        format!("…{}", &shortened[start..])
    } else {
        shortened
    }
}

fn fmt_tok(n: u32) -> String {
    if n >= 1000 { format!("{:.1}k", n as f32 / 1000.0) } else { n.to_string() }
}
