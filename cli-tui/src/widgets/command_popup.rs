use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Clear, Paragraph},
};
use crate::app::App;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

/// Returns commands whose name (after `/`) starts with `filter`.
pub fn filtered_commands(filter: &str) -> Vec<(&'static str, &'static str)> {
    const COMMANDS: &[(&str, &str)] = &[
        ("/model ", "切换模型"),
        ("/clear", "清空会话历史"),
        ("/system ", "设置 system prompt"),
        ("/help", "显示全部命令"),
        ("/export", "导出会话为 JSON"),
    ];
    COMMANDS
        .iter()
        .filter(|(cmd, _)| {
            let name = &cmd[1..]; // strip leading '/'
            name.starts_with(filter) || filter.is_empty()
        })
        .copied()
        .collect()
}

pub fn draw(f: &mut Frame, input_area: Rect, app: &App) {
    let popup_state = match &app.command_popup {
        Some(s) => s,
        None => return,
    };

    let cmds = filtered_commands(&popup_state.filter);
    if cmds.is_empty() {
        return;
    }

    // Clamp selected index
    let selected = popup_state.selected.min(cmds.len().saturating_sub(1));

    let popup_height = (cmds.len() as u16 + 2).min(8);
    // Place popup directly above the input area
    let y = input_area.y.saturating_sub(popup_height);
    let popup_area = Rect {
        x: input_area.x,
        y,
        width: input_area.width,
        height: popup_height,
    };

    f.render_widget(Clear, popup_area);

    let lines: Vec<Line> = cmds
        .iter()
        .enumerate()
        .map(|(i, (cmd, desc))| {
            if i == selected {
                Line::from(vec![
                    Span::styled(
                        format!(" {} ", cmd),
                        Style::default().fg(Color::Black).bg(ACCENT).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(
                        format!(" {}", desc),
                        Style::default().fg(Color::Black).bg(ACCENT),
                    ),
                ])
            } else {
                Line::from(vec![
                    Span::styled(format!(" {} ", cmd), Style::default().fg(ACCENT)),
                    Span::styled(format!(" {}", desc), Style::default().fg(Color::DarkGray)),
                ])
            }
        })
        .collect();

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(ACCENT))
        .title(Span::styled(" Commands ", Style::default().fg(ACCENT)));

    f.render_widget(Paragraph::new(Text::from(lines)).block(block), popup_area);
}
