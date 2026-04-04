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
    if area.width >= 78 {
        let logo_lines: Vec<Line> = LOGO
            .iter()
            .map(|row| Line::from(Span::styled(*row, Style::default().fg(ACCENT))))
            .collect();
        f.render_widget(Paragraph::new(logo_lines), chunks[1]);
    }

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
