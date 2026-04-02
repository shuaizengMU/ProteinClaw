use ratatui::{Frame, layout::Rect};
use crate::app::App;

pub fn draw(f: &mut Frame, input_area: Rect, app: &App) {
    let _ = (f, input_area, app);
}

/// Returns the list of commands filtered by `filter` (text after '/').
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
        .filter(|(cmd, _)| cmd[1..].starts_with(filter))
        .copied()
        .collect()
}
