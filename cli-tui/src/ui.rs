use ratatui::{
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Wrap},
    Frame,
};
use tui_textarea::TextArea;

use crate::app::{App, Screen, SetupState, SetupStep};
use crate::registry::PROVIDERS;
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

// ── Setup wizard ─────────────────────────────────────────────────────────────

fn draw_setup(f: &mut Frame, st: &SetupState) {
    let area = f.area();
    let popup_h: u16 = match st.step {
        SetupStep::Provider => (PROVIDERS.len() as u16 + 6).min(area.height),
        SetupStep::Model => {
            let n = PROVIDERS[st.provider_idx].models.len() as u16;
            (n + 8).min(area.height)
        }
        SetupStep::ApiKey => 12u16.min(area.height),
    };
    let popup_w: u16 = 50.min(area.width);
    let vpad = area.height.saturating_sub(popup_h) / 2;
    let hpad = area.width.saturating_sub(popup_w) / 2;
    let popup = Rect { x: hpad, y: vpad, width: popup_w, height: popup_h };

    f.render_widget(Clear, popup);

    let title = match st.step {
        SetupStep::Provider => " Setup — 1/3 Provider ",
        SetupStep::Model    => " Setup — 2/3 Model ",
        SetupStep::ApiKey   => " Setup — 3/3 API Key ",
    };
    let block = Block::default()
        .title(title)
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::Cyan));
    f.render_widget(block, popup);

    let inner = Rect {
        x: popup.x + 2,
        y: popup.y + 1,
        width: popup.width.saturating_sub(4),
        height: popup.height.saturating_sub(2),
    };

    match st.step {
        SetupStep::Provider => draw_setup_provider(f, inner, st),
        SetupStep::Model    => draw_setup_model(f, inner, st),
        SetupStep::ApiKey   => draw_setup_api_key(f, inner, st),
    }
}

fn draw_setup_provider(f: &mut Frame, area: Rect, st: &SetupState) {
    let mut lines: Vec<Line> = vec![
        Line::from(Span::styled("Select a provider:", Style::default().fg(Color::Yellow))),
        Line::raw(""),
    ];
    for (i, p) in PROVIDERS.iter().enumerate() {
        let marker = if i == st.provider_idx { "> " } else { "  " };
        let style = if i == st.provider_idx {
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
        } else {
            Style::default()
        };
        lines.push(Line::from(Span::styled(format!("{}{}", marker, p.name), style)));
    }
    lines.push(Line::raw(""));
    lines.push(Line::from(vec![
        Span::styled("[↑↓]", Style::default().fg(Color::Cyan)),
        Span::raw(" select  "),
        Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
        Span::raw(" confirm"),
    ]));
    if let Some(err) = &st.error {
        lines.push(Line::from(Span::styled(err.as_str(), Style::default().fg(Color::Red))));
    }
    f.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), area);
}

fn draw_setup_model(f: &mut Frame, area: Rect, st: &SetupState) {
    let provider = &PROVIDERS[st.provider_idx];
    let mut lines: Vec<Line> = vec![
        Line::from(vec![
            Span::raw("Provider: "),
            Span::styled(provider.name, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(Span::styled("Select a model:", Style::default().fg(Color::Yellow))),
        Line::raw(""),
    ];
    for (i, m) in provider.models.iter().enumerate() {
        let marker = if i == st.model_idx { "> " } else { "  " };
        let style = if i == st.model_idx {
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)
        } else {
            Style::default()
        };
        let label = if m.tag.is_empty() {
            m.name.to_string()
        } else {
            format!("{} {}", m.name, m.tag)
        };
        lines.push(Line::from(Span::styled(format!("{}{}", marker, label), style)));
    }
    lines.push(Line::raw(""));
    lines.push(Line::from(vec![
        Span::styled("[↑↓]", Style::default().fg(Color::Cyan)),
        Span::raw(" select  "),
        Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
        Span::raw(" confirm  "),
        Span::styled("[Esc]", Style::default().fg(Color::Cyan)),
        Span::raw(" back"),
    ]));
    if let Some(err) = &st.error {
        lines.push(Line::from(Span::styled(err.as_str(), Style::default().fg(Color::Red))));
    }
    f.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), area);
}

fn draw_setup_api_key(f: &mut Frame, area: Rect, st: &SetupState) {
    let provider = &PROVIDERS[st.provider_idx];
    let model = &provider.models[st.model_idx];

    // Mask key: show first 6 chars, rest as asterisks
    let masked = if st.key_buf.len() <= 6 {
        st.key_buf.clone()
    } else {
        let visible = &st.key_buf[..6];
        format!("{}{}", visible, "*".repeat(st.key_buf.len() - 6))
    };

    let mut lines: Vec<Line> = vec![
        Line::from(vec![
            Span::raw("Provider: "),
            Span::styled(provider.name, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::raw("Model:    "),
            Span::styled(model.name, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]),
        Line::raw(""),
        Line::from(Span::styled(
            format!("Enter your {}:", provider.env_var),
            Style::default().fg(Color::Yellow),
        )),
        Line::from(vec![
            Span::styled(&masked, Style::default().fg(Color::White)),
            Span::styled("_", Style::default().fg(Color::Green).add_modifier(Modifier::SLOW_BLINK)),
        ]),
        Line::raw(""),
        Line::from(vec![
            Span::styled("[Enter]", Style::default().fg(Color::Cyan)),
            Span::raw(" save  "),
            Span::styled("[Esc]", Style::default().fg(Color::Cyan)),
            Span::raw(" back"),
        ]),
    ];
    if let Some(err) = &st.error {
        lines.push(Line::from(Span::styled(err.as_str(), Style::default().fg(Color::Red))));
    }
    f.render_widget(Paragraph::new(lines).wrap(Wrap { trim: false }), area);
}
