use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    Frame,
    layout::{Constraint, Layout},
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, Paragraph, Wrap},
};
use serde_json::Value;
use tokio::sync::mpsc::Sender;

use crate::events::{AgentEvent, HistoryEntry, WsQuery};

#[derive(Debug, Clone)]
pub enum AgentState {
    Ready,
    Thinking,
    Error(String),
}

#[derive(Debug, Clone)]
pub enum Message {
    User(String),
    Thinking(String),
    AssistantToken(String),
    ToolCall { tool: String, args: Value, result: Option<Value> },
    SystemInfo(String),
    Error(String),
}

pub enum MainAction {
    Quit,
}

pub struct MainState {
    pub model: String,
    pub agent_state: AgentState,
    pub messages: Vec<Message>,
    pub input: String,
    pub input_cursor: usize,
    pub scroll_offset: u16,
    ws_tx: Sender<String>,
    history: Vec<HistoryEntry>,
}

impl MainState {
    pub fn new(model: String, ws_tx: Sender<String>) -> Self {
        Self {
            model,
            agent_state: AgentState::Ready,
            messages: Vec::new(),
            input: String::new(),
            input_cursor: 0,
            scroll_offset: 0,
            ws_tx,
            history: Vec::new(),
        }
    }

    /// Handle a key event. Returns `Some(MainAction)` when the app should quit.
    pub fn handle_key(&mut self, key: KeyEvent) -> Option<MainAction> {
        match key.code {
            KeyCode::Char(c) => {
                self.input.insert(self.input_cursor, c);
                self.input_cursor += 1;
            }
            KeyCode::Backspace => {
                if self.input_cursor > 0 {
                    self.input_cursor -= 1;
                    self.input.remove(self.input_cursor);
                }
            }
            KeyCode::Left => {
                self.input_cursor = self.input_cursor.saturating_sub(1);
            }
            KeyCode::Right => {
                if self.input_cursor < self.input.len() {
                    self.input_cursor += 1;
                }
            }
            KeyCode::Up => {
                self.scroll_offset = self.scroll_offset.saturating_sub(1);
            }
            KeyCode::Down => {
                self.scroll_offset = self.scroll_offset.saturating_add(1);
            }
            KeyCode::Enter => {
                let query = self.input.trim().to_string();
                self.input.clear();
                self.input_cursor = 0;
                if query.is_empty() { return None; }
                return self.submit(query);
            }
            _ => {}
        }
        None
    }

    fn submit(&mut self, query: String) -> Option<MainAction> {
        if query.starts_with('/') {
            return self.handle_slash(&query);
        }
        // Add user message to display
        self.messages.push(Message::User(query.clone()));
        // Build WS payload: history is all turns BEFORE current query
        let payload = WsQuery {
            message: query.clone(),
            history: self.history.clone(),
            model: self.model.clone(),
        };
        self.history.push(HistoryEntry { role: "user".into(), content: query });
        let json = serde_json::to_string(&payload).unwrap_or_default();
        let _ = self.ws_tx.try_send(json);
        self.agent_state = AgentState::Thinking;
        None
    }

    fn handle_slash(&mut self, cmd: &str) -> Option<MainAction> {
        let parts: Vec<&str> = cmd.split_whitespace().collect();
        match parts.first().copied() {
            Some("/exit") => return Some(MainAction::Quit),
            Some("/clear") => {
                self.messages.clear();
                self.history.clear();
            }
            Some("/model") => {
                if parts.len() < 2 {
                    self.messages.push(Message::SystemInfo(
                        "Usage: /model <name>".into()
                    ));
                } else {
                    self.model = parts[1].to_string();
                    self.messages.push(Message::SystemInfo(
                        format!("Switched to model: {}", self.model)
                    ));
                }
            }
            Some("/tools") => {
                self.messages.push(Message::SystemInfo(
                    "Tools: uniprot (UniProt lookup), blast (BLAST search)".into()
                ));
            }
            _ => {
                self.messages.push(Message::SystemInfo(
                    format!("Unknown command '{}'. Try /model /tools /clear /exit", cmd)
                ));
            }
        }
        None
    }

    /// Handle an event received from the WebSocket.
    pub fn handle_agent_event(&mut self, event: AgentEvent) {
        match event {
            AgentEvent::Thinking(text) => {
                self.messages.push(Message::Thinking(text));
            }
            AgentEvent::Token(text) => {
                // Accumulate into the last AssistantToken or create a new one
                if let Some(Message::AssistantToken(ref mut existing)) = self.messages.last_mut() {
                    existing.push_str(&text);
                } else {
                    self.messages.push(Message::AssistantToken(text.clone()));
                }
            }
            AgentEvent::ToolCall { tool, args } => {
                self.messages.push(Message::ToolCall { tool, args, result: None });
            }
            AgentEvent::Observation { result } => {
                // Set result on the last ToolCall
                for msg in self.messages.iter_mut().rev() {
                    if let Message::ToolCall { result: ref mut r, .. } = msg {
                        if r.is_none() { *r = Some(result); break; }
                    }
                }
            }
            AgentEvent::Done => {
                self.agent_state = AgentState::Ready;
                // Collect assistant response tokens and add to history
                let response: String = self.messages.iter().rev()
                    .take_while(|m| !matches!(m, Message::User(_)))
                    .filter_map(|m| if let Message::AssistantToken(t) = m { Some(t.as_str()) } else { None })
                    .collect::<Vec<_>>().into_iter().rev().collect();
                if !response.is_empty() {
                    self.history.push(HistoryEntry { role: "assistant".into(), content: response });
                }
            }
            AgentEvent::Error(msg) => {
                self.agent_state = AgentState::Error(msg.clone());
                self.messages.push(Message::Error(msg));
            }
        }
    }

    fn agent_state_str(&self) -> &str {
        match &self.agent_state {
            AgentState::Ready    => "ready",
            AgentState::Thinking => "thinking...",
            AgentState::Error(_) => "error",
        }
    }
}

pub fn draw(frame: &mut Frame, state: &MainState) {
    let chunks = Layout::vertical([
        Constraint::Length(1), // status bar
        Constraint::Min(0),    // conversation
        Constraint::Length(3), // input
    ])
    .split(frame.area());

    // Status bar
    let status = format!(
        " ProteinClaw  {}  model: {} — {} ",
        "─".repeat(10),
        state.model,
        state.agent_state_str(),
    );
    frame.render_widget(
        Paragraph::new(status).style(Style::default().bg(Color::DarkGray).fg(Color::White)),
        chunks[0],
    );

    // Conversation
    let text = build_conversation_text(&state.messages);
    let conv = Paragraph::new(text)
        .wrap(Wrap { trim: false })
        .scroll((state.scroll_offset, 0));
    frame.render_widget(conv, chunks[1]);

    // Input box
    let input_block = Block::default()
        .borders(Borders::TOP)
        .title(" Ask ProteinClaw... (/model /tools /clear /exit) ");
    let input_inner = input_block.inner(chunks[2]);
    frame.render_widget(input_block, chunks[2]);
    frame.render_widget(
        Paragraph::new(state.input.as_str()),
        input_inner,
    );
    // Cursor
    frame.set_cursor_position((
        input_inner.x + state.input_cursor as u16,
        input_inner.y,
    ));
}

fn build_conversation_text(messages: &[Message]) -> Text<'_> {
    let mut lines: Vec<Line<'_>> = Vec::new();
    for msg in messages {
        match msg {
            Message::User(text) => {
                lines.push(Line::from(vec![
                    Span::styled(format!("> {}", text), Style::default().fg(Color::Blue).add_modifier(Modifier::BOLD)),
                ]));
                lines.push(Line::from(""));
            }
            Message::Thinking(text) => {
                lines.push(Line::from(vec![
                    Span::styled(text.as_str(), Style::default().fg(Color::DarkGray).add_modifier(Modifier::ITALIC)),
                ]));
            }
            Message::AssistantToken(text) => {
                for line in text.lines() {
                    lines.push(Line::from(line.to_string()));
                }
                lines.push(Line::from(""));
            }
            Message::ToolCall { tool, args, result } => {
                let args_str = serde_json::to_string(args).unwrap_or_default();
                let tool_style = Style::default().fg(Color::Cyan);
                lines.push(Line::from(vec![
                    Span::styled(format!("╔═ tool: {} ═══", tool), tool_style),
                ]));
                lines.push(Line::from(vec![
                    Span::styled(format!("║  args: {}", args_str), tool_style),
                ]));
                if let Some(r) = result {
                    let r_str = serde_json::to_string(r).unwrap_or_default();
                    let truncated = if r_str.len() > 80 { format!("{}...", &r_str[..80]) } else { r_str };
                    lines.push(Line::from(vec![
                        Span::styled(format!("║  result: {}", truncated), tool_style),
                    ]));
                } else {
                    lines.push(Line::from(vec![
                        Span::styled("║  (waiting for result...)", Style::default().fg(Color::DarkGray)),
                    ]));
                }
                lines.push(Line::from(vec![
                    Span::styled("╚═══════════════════", tool_style),
                ]));
                lines.push(Line::from(""));
            }
            Message::SystemInfo(text) => {
                lines.push(Line::from(vec![
                    Span::styled(text.as_str(), Style::default().fg(Color::Yellow)),
                ]));
            }
            Message::Error(text) => {
                lines.push(Line::from(vec![
                    Span::styled(text.as_str(), Style::default().fg(Color::Red)),
                ]));
            }
        }
    }
    Text::from(lines)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use tokio::sync::mpsc;

    fn key(code: KeyCode) -> KeyEvent {
        KeyEvent::new(code, KeyModifiers::empty())
    }

    fn make_state() -> MainState {
        let (tx, _rx) = mpsc::channel(8);
        MainState::new("deepseek-chat".into(), tx)
    }

    #[test]
    fn new_state_is_empty() {
        let state = make_state();
        assert!(state.messages.is_empty());
        assert!(state.input.is_empty());
        assert!(matches!(state.agent_state, AgentState::Ready));
    }

    #[test]
    fn typing_appends_to_input() {
        let mut state = make_state();
        state.handle_key(key(KeyCode::Char('h')));
        state.handle_key(key(KeyCode::Char('i')));
        assert_eq!(state.input, "hi");
    }

    #[test]
    fn backspace_removes_last_char() {
        let mut state = make_state();
        state.handle_key(key(KeyCode::Char('h')));
        state.handle_key(key(KeyCode::Char('i')));
        state.handle_key(key(KeyCode::Backspace));
        assert_eq!(state.input, "h");
    }

    #[test]
    fn enter_clears_input_and_adds_user_message() {
        let mut state = make_state();
        state.handle_key(key(KeyCode::Char('h')));
        state.handle_key(key(KeyCode::Char('i')));
        state.handle_key(key(KeyCode::Enter));
        assert!(state.input.is_empty());
        assert!(matches!(&state.messages[0], Message::User(s) if s == "hi"));
    }

    #[test]
    fn token_event_creates_assistant_message() {
        let mut state = make_state();
        state.handle_agent_event(crate::events::AgentEvent::Token("Hello".into()));
        assert!(matches!(&state.messages[0], Message::AssistantToken(s) if s == "Hello"));
    }

    #[test]
    fn consecutive_tokens_accumulate() {
        let mut state = make_state();
        state.handle_agent_event(crate::events::AgentEvent::Token("Hello ".into()));
        state.handle_agent_event(crate::events::AgentEvent::Token("world".into()));
        assert_eq!(state.messages.len(), 1);
        assert!(matches!(&state.messages[0], Message::AssistantToken(s) if s == "Hello world"));
    }

    #[test]
    fn done_event_sets_state_ready() {
        let mut state = make_state();
        state.agent_state = AgentState::Thinking;
        state.handle_agent_event(crate::events::AgentEvent::Done);
        assert!(matches!(state.agent_state, AgentState::Ready));
    }

    #[test]
    fn clear_command_empties_messages() {
        let mut state = make_state();
        state.handle_agent_event(crate::events::AgentEvent::Token("hi".into()));
        let _ = state.handle_key(key(KeyCode::Char('/')));
        let _ = state.handle_key(key(KeyCode::Char('c')));
        let _ = state.handle_key(key(KeyCode::Char('l')));
        let _ = state.handle_key(key(KeyCode::Char('e')));
        let _ = state.handle_key(key(KeyCode::Char('a')));
        let _ = state.handle_key(key(KeyCode::Char('r')));
        let result = state.handle_key(key(KeyCode::Enter));
        assert!(result.is_none()); // no quit action
        assert!(state.messages.is_empty());
    }

    #[test]
    fn exit_command_returns_quit_action() {
        let mut state = make_state();
        for c in "/exit".chars() {
            state.handle_key(key(KeyCode::Char(c)));
        }
        let result = state.handle_key(key(KeyCode::Enter));
        assert!(matches!(result, Some(MainAction::Quit)));
    }
}
