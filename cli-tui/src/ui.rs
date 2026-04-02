use ratatui::{
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Wrap},
    Frame,
};
use tui_textarea::TextArea;

use crate::app::{App, Screen, SetupState};
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

// ── Setup wizard (unchanged from original) ───────────────────────────────────

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
