use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Paragraph, Wrap},
};
use crate::app::{App, AssistantPart, ChatMessage};

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let mut lines: Vec<Line> = Vec::new();

    for msg in app.messages.iter() {
        if let ChatMessage::Assistant { parts, .. } = msg {
            for part in parts.iter() {
                if let AssistantPart::ToolCall { tool, args, result, .. } = part {
                    let (status, color) = if result.is_some() {
                        ("⏺", Color::Green)
                    } else {
                        ("⟳", Color::Yellow)
                    };
                    lines.push(Line::from(vec![
                        Span::styled(status, Style::default().fg(color)),
                        Span::raw(" "),
                        Span::styled(tool.as_str(), Style::default().add_modifier(Modifier::BOLD)),
                    ]));

                    // Show first arg key=value, truncated to fit sidebar
                    if let Some(obj) = args.as_object() {
                        if let Some((k, v)) = obj.iter().next() {
                            let val = v.as_str().unwrap_or(&v.to_string()).to_string();
                            let val = if val.chars().count() > 18 {
                                let end = val.char_indices().nth(15).map(|(i, _)| i).unwrap_or(val.len());
                                format!("{}…", &val[..end])
                            } else {
                                val
                            };
                            lines.push(Line::from(Span::styled(
                                format!("  {}={}", k, val),
                                Style::default().fg(Color::DarkGray),
                            )));
                        }
                    }

                    // Show result summary
                    if let Some(res) = result {
                        let summary = res.lines().next().unwrap_or("").trim();
                        let summary = if summary.chars().count() > 20 {
                            let end = summary.char_indices().nth(17).map(|(i, _)| i).unwrap_or(summary.len());
                            format!("{}…", &summary[..end])
                        } else {
                            summary.to_string()
                        };
                        lines.push(Line::from(Span::styled(
                            format!("  → {}", summary),
                            Style::default().fg(Color::DarkGray),
                        )));
                    }

                    lines.push(Line::raw(""));
                }
            }
        }
    }

    if lines.is_empty() {
        lines.push(Line::raw(""));
        lines.push(Line::from(Span::styled(
            " No tool calls yet",
            Style::default().fg(Color::DarkGray),
        )));
    }

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(" Tool Calls ", Style::default().fg(Color::DarkGray)));

    let para = Paragraph::new(Text::from(lines))
        .block(block)
        .wrap(Wrap { trim: true });

    f.render_widget(para, area);
}
