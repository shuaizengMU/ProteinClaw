use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Paragraph, Wrap},
};
use crate::app::{App, AssistantPart, ChatMessage};
use super::LayoutMode;

pub fn draw(f: &mut Frame, area: Rect, app: &App) {
    let mode = LayoutMode::from_width(area.width);
    let width = area.width.saturating_sub(2) as usize;
    let mut all_lines: Vec<Line> = Vec::new();

    for msg in app.messages.iter() {
        match msg {
            ChatMessage::User(text) => {
                const USER_BG: Color = Color::Rgb(55, 55, 55);
                all_lines.push(Line::raw(""));
                all_lines.push(Line::from(vec![
                    Span::styled("> ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD).bg(USER_BG)),
                    Span::styled(text.as_str(), Style::default().add_modifier(Modifier::BOLD).bg(USER_BG)),
                ]));
                all_lines.push(Line::raw(""));
            }

            ChatMessage::Assistant { parts, done, elapsed } => {
                let mut first_text = true;
                for (pi, part) in parts.iter().enumerate() {
                    match part {
                        AssistantPart::Text(text) => {
                            let mut md = render_markdown(text, width);
                            if first_text {
                                if let Some(first_line) = md.first_mut() {
                                    first_line.spans.insert(0, Span::styled("● ", Style::default().fg(Color::Cyan)));
                                }
                                first_text = false;
                            }
                            if !*done && pi == parts.len() - 1 {
                                if let Some(last) = md.last_mut() {
                                    last.spans.push(Span::styled("█", Style::default().fg(Color::White)));
                                } else {
                                    md.push(Line::from(Span::styled("█", Style::default().fg(Color::White))));
                                }
                            }
                            all_lines.extend(md);
                        }
                        AssistantPart::Thinking { content, expanded } => {
                            if *expanded {
                                all_lines.push(Line::from(vec![
                                    Span::styled("∴ ", Style::default().fg(Color::Magenta)),
                                    Span::styled("Thinking  [ctrl+o to collapse]", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
                                ]));
                                for line in render_markdown(content, width) {
                                    all_lines.push(line.patch_style(Style::default().fg(Color::DarkGray)));
                                }
                            } else {
                                all_lines.push(Line::from(vec![
                                    Span::styled("∴ ", Style::default().fg(Color::Magenta)),
                                    Span::styled("Thinking…  (ctrl+o to expand)", Style::default().fg(Color::DarkGray)),
                                ]));
                            }
                            all_lines.push(Line::raw(""));
                        }
                        AssistantPart::ToolCall { tool, args, result, expanded } => {
                            let (status, status_color) = if result.is_some() {
                                ("⏺", Color::Green)
                            } else {
                                ("⟳", Color::Yellow)
                            };
                            all_lines.push(Line::from(vec![
                                Span::styled(status, Style::default().fg(status_color)),
                                Span::raw("  "),
                                Span::styled(tool.as_str(), Style::default().add_modifier(Modifier::BOLD)),
                                Span::styled("  [enter to toggle]", Style::default().fg(Color::DarkGray)),
                            ]));
                            if *expanded {
                                let args_str = serde_json::to_string_pretty(args).unwrap_or_else(|_| args.to_string());
                                for line in args_str.lines() {
                                    all_lines.push(Line::from(vec![
                                        Span::raw("    "),
                                        Span::styled(line.to_string(), Style::default().fg(Color::Cyan)),
                                    ]));
                                }
                                if let Some(res) = result {
                                    all_lines.push(Line::from(Span::styled("  → result:", Style::default().fg(Color::DarkGray))));
                                    for line in res.lines() {
                                        all_lines.push(Line::from(vec![
                                            Span::raw("    "),
                                            Span::styled(line.to_string(), Style::default().fg(Color::DarkGray)),
                                        ]));
                                    }
                                }
                            }
                            all_lines.push(Line::raw(""));
                        }
                    }
                }
                if parts.is_empty() && !*done {
                    const SPINNER: &[&str] = &["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"];
                    let frame = (app.tick / 5) as usize % SPINNER.len();
                    all_lines.push(Line::from(vec![
                        Span::styled(SPINNER[frame], Style::default().fg(Color::Cyan)),
                        Span::styled(" Thinking...", Style::default().fg(Color::DarkGray)),
                    ]));
                }
                if *done {
                    if let Some(secs) = elapsed {
                        let m = secs / 60;
                        let s = secs % 60;
                        let duration = if m > 0 {
                            format!("{}m {}s", m, s)
                        } else {
                            format!("{}s", s)
                        };
                        all_lines.push(Line::from(Span::styled(
                            format!("✻ Cooked for {}", duration),
                            Style::default().fg(Color::DarkGray),
                        )));
                    }
                }
            }

            ChatMessage::Error(msg) => {
                all_lines.push(Line::raw(""));
                all_lines.push(Line::from(Span::styled("✗ Error", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))));
                all_lines.push(Line::from(vec![
                    Span::raw("  "),
                    Span::styled(msg.as_str(), Style::default().fg(Color::Red)),
                ]));
                all_lines.push(Line::raw(""));
            }
        }
    }

    if app.messages.is_empty() {
        super::welcome::draw(f, area);
        return;
    }

    let inner_height = area.height.saturating_sub(2) as usize;
    let total = all_lines.len();

    // Each logical line may wrap into multiple visual rows. Compute the visual
    // row count per line so that scroll_offset and max_offset operate in visual
    // space, not logical-line space (which undershoots on long/wrapped content).
    let vrows: Vec<usize> = all_lines.iter().map(|l| {
        let w: usize = l.spans.iter().map(|s| s.content.chars().count()).sum();
        if width == 0 || w == 0 { 1 } else { (w + width - 1) / width }
    }).collect();
    let total_visual: usize = vrows.iter().sum::<usize>().max(1);

    let max_offset = total_visual.saturating_sub(inner_height);
    let offset = app.scroll_offset.min(max_offset);

    // Find the logical line whose visual top matches the scroll target.
    let target_top_visual = total_visual.saturating_sub(inner_height + offset);
    let scroll_from_top = {
        let mut acc = 0usize;
        let mut result = 0usize;
        for (i, &r) in vrows.iter().enumerate() {
            if acc >= target_top_visual { result = i; break; }
            acc += r;
            result = i + 1;
        }
        result.min(total)
    };

    let block = match mode {
        LayoutMode::Compact => Block::default().borders(Borders::NONE),
        _ => Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::DarkGray))
            .title(Span::styled(" Transcript ", Style::default().fg(Color::DarkGray))),
    };

    let para = Paragraph::new(Text::from(all_lines))
        .block(block)
        .wrap(Wrap { trim: false })
        .scroll((scroll_from_top as u16, 0));

    f.render_widget(para, area);
}

pub fn render_markdown(text: &str, _width: usize) -> Vec<Line<'static>> {
    use pulldown_cmark::{Event, Options, Parser, Tag, TagEnd};

    let mut lines: Vec<Line<'static>> = Vec::new();
    let mut current: Vec<Span<'static>> = Vec::new();
    let mut bold = false;
    let mut italic = false;
    let mut in_code_block = false;
    let mut in_item = false;
    let mut heading_level: u32 = 0;

    macro_rules! flush {
        () => {
            if !current.is_empty() {
                lines.push(Line::from(std::mem::take(&mut current)));
            }
        };
    }

    macro_rules! push_span {
        ($s:expr) => {{
            let mut style = Style::default();
            if bold { style = style.add_modifier(Modifier::BOLD); }
            if italic { style = style.add_modifier(Modifier::ITALIC); }
            if heading_level > 0 {
                style = style.add_modifier(Modifier::BOLD).add_modifier(Modifier::UNDERLINED).fg(Color::White);
            }
            current.push(Span::styled($s.to_string(), style));
        }};
    }

    for event in Parser::new_ext(text, Options::all()) {
        match event {
            Event::Start(Tag::Heading { level, .. }) => { flush!(); heading_level = level as u32; }
            Event::End(TagEnd::Heading(_)) => { flush!(); lines.push(Line::raw("")); heading_level = 0; }
            Event::Start(Tag::Paragraph) => {}
            Event::End(TagEnd::Paragraph) => { flush!(); lines.push(Line::raw("")); }
            Event::Start(Tag::CodeBlock(_)) => { in_code_block = true; flush!(); }
            Event::End(TagEnd::CodeBlock) => { in_code_block = false; lines.push(Line::raw("")); }
            Event::Start(Tag::List(_)) => {}
            Event::End(TagEnd::List(_)) => { lines.push(Line::raw("")); }
            Event::Start(Tag::Item) => { in_item = true; current.push(Span::raw("  • ")); }
            Event::End(TagEnd::Item) => { in_item = false; flush!(); }
            Event::Start(Tag::BlockQuote(_)) => { current.push(Span::styled("▏ ", Style::default().fg(Color::DarkGray))); }
            Event::End(TagEnd::BlockQuote(_)) => { flush!(); }
            Event::Start(Tag::Strong) => bold = true,
            Event::End(TagEnd::Strong) => bold = false,
            Event::Start(Tag::Emphasis) => italic = true,
            Event::End(TagEnd::Emphasis) => italic = false,
            Event::Start(Tag::Link { .. }) | Event::End(TagEnd::Link) => {}
            Event::Text(t) => {
                if in_code_block {
                    for line in t.lines() {
                        lines.push(Line::from(vec![
                            Span::styled("  ", Style::default().bg(Color::DarkGray)),
                            Span::styled(line.to_string(), Style::default().fg(Color::Cyan).bg(Color::DarkGray)),
                            Span::styled("  ", Style::default().bg(Color::DarkGray)),
                        ]));
                    }
                } else {
                    push_span!(t);
                }
            }
            Event::Code(c) => { current.push(Span::styled(c.to_string(), Style::default().fg(Color::Cyan))); }
            Event::SoftBreak => { current.push(Span::raw(" ")); }
            Event::HardBreak => { flush!(); }
            Event::Rule => {
                flush!();
                lines.push(Line::from(Span::styled("─".repeat(40), Style::default().fg(Color::DarkGray))));
            }
            _ => {}
        }
        let _ = in_item;
    }
    flush!();
    lines
}
