use ratatui::{
    Frame,
    layout::Rect,
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Clear, Paragraph},
};
use crate::app::App;
use crate::registry::PROVIDERS;

const ACCENT: Color = Color::Rgb(0x00, 0xb0, 0xaa);

/// A popup entry: either a slash command or a model to pick.
#[derive(Debug, Clone)]
pub struct PopupEntry {
    pub display: String,
    pub description: String,
    /// If this is a model entry, (provider_idx, model_idx). None for commands.
    pub model: Option<(usize, usize)>,
}

const COMMANDS: &[(&str, &str)] = &[
    ("/model ", "切换模型"),
    ("/clear", "清空会话历史"),
    ("/system ", "设置 system prompt"),
    ("/help", "显示全部命令"),
    ("/export", "导出会话为 JSON"),
];

/// Returns popup entries based on the current filter text (after the leading `/`).
///
/// When the filter is "model" or "model <sub>", returns a flat list of all
/// models (optionally filtered by sub-string) instead of the `/model` command.
pub fn filtered_entries(filter: &str) -> Vec<PopupEntry> {
    // Check if we're in model-picker mode: filter is exactly "model", "model ",
    // or "model <something>"
    let model_filter = if filter == "model" || filter.starts_with("model ") {
        Some(filter.strip_prefix("model").unwrap().trim())
    } else {
        None
    };

    if let Some(sub) = model_filter {
        // Model-picker mode: flat list of "Provider — model_name"
        let mut entries = Vec::new();
        for (pi, provider) in PROVIDERS.iter().enumerate() {
            for (mi, model) in provider.models.iter().enumerate() {
                let display = format!("{} — {}", provider.name, model.name);
                let tag_suffix = if model.tag.is_empty() {
                    String::new()
                } else {
                    format!("  {}", model.tag)
                };
                // Check if API key already set for this provider
                let has_key = provider.env_var.is_empty()
                    || std::env::var(provider.env_var)
                        .map(|v| !v.is_empty())
                        .unwrap_or(false);
                let key_hint = if has_key { "✓" } else { "🔑" };
                let description = format!("{}{}", key_hint, tag_suffix);

                // Apply sub-filter: match against provider name or model name
                if !sub.is_empty() {
                    let lower_sub = sub.to_lowercase();
                    let matches = provider.name.to_lowercase().contains(&lower_sub)
                        || model.name.to_lowercase().contains(&lower_sub);
                    if !matches {
                        continue;
                    }
                }

                entries.push(PopupEntry {
                    display,
                    description,
                    model: Some((pi, mi)),
                });
            }
        }
        entries
    } else {
        // Normal command mode
        COMMANDS
            .iter()
            .filter(|(cmd, _)| {
                let name = &cmd[1..]; // strip leading '/'
                name.starts_with(filter) || filter.is_empty()
            })
            .map(|(cmd, desc)| PopupEntry {
                display: cmd.to_string(),
                description: desc.to_string(),
                model: None,
            })
            .collect()
    }
}

pub fn draw(f: &mut Frame, input_area: Rect, app: &App) {
    let popup_state = match &app.command_popup {
        Some(s) => s,
        None => return,
    };

    let entries = filtered_entries(&popup_state.filter);
    if entries.is_empty() {
        return;
    }

    let selected = popup_state.selected.min(entries.len().saturating_sub(1));

    // Model picker can have many entries — allow taller popup
    let max_height = if entries.first().map(|e| e.model.is_some()).unwrap_or(false) {
        16u16
    } else {
        8u16
    };
    let popup_height = (entries.len() as u16 + 2).min(max_height);
    let y = input_area.y.saturating_sub(popup_height);
    let popup_area = Rect {
        x: input_area.x,
        y,
        width: input_area.width,
        height: popup_height,
    };

    f.render_widget(Clear, popup_area);

    // If we have more entries than visible rows, compute scroll window
    let visible_rows = (popup_height.saturating_sub(2)) as usize; // minus borders
    let scroll_start = if selected >= visible_rows {
        selected - visible_rows + 1
    } else {
        0
    };

    let lines: Vec<Line> = entries
        .iter()
        .enumerate()
        .skip(scroll_start)
        .take(visible_rows)
        .map(|(i, entry)| {
            if i == selected {
                Line::from(vec![
                    Span::styled(
                        format!(" {} ", entry.display),
                        Style::default().fg(Color::Black).bg(ACCENT).add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(
                        format!(" {}", entry.description),
                        Style::default().fg(Color::Black).bg(ACCENT),
                    ),
                ])
            } else {
                Line::from(vec![
                    Span::styled(format!(" {} ", entry.display), Style::default().fg(ACCENT)),
                    Span::styled(format!(" {}", entry.description), Style::default().fg(Color::DarkGray)),
                ])
            }
        })
        .collect();

    let is_model_mode = entries.first().map(|e| e.model.is_some()).unwrap_or(false);
    let title = if is_model_mode { " Models " } else { " Commands " };

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(ACCENT))
        .title(Span::styled(title, Style::default().fg(ACCENT)));

    f.render_widget(Paragraph::new(Text::from(lines)).block(block), popup_area);
}
