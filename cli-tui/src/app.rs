use crate::config::Config;
use crate::events::WsEvent;
use serde_json::Value;

// ── Message model ────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub enum AssistantPart {
    Text(String),
    Thinking {
        content: String,
        expanded: bool,
    },
    ToolCall {
        #[allow(dead_code)]
        tool: String,
        args: Value,
        result: Option<String>,
        expanded: bool,
    },
}

#[derive(Debug, Clone)]
pub enum ChatMessage {
    User(String),
    Assistant { parts: Vec<AssistantPart>, done: bool },
    Error(String),
}

// ── Connection state ─────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum ConnStatus {
    Connecting,
    Connected,
    Disconnected,
}

// ── Command popup state ───────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct CommandPopupState {
    pub filter: String,
    pub selected: usize,
}

impl CommandPopupState {
    pub fn new() -> Self {
        Self { filter: String::new(), selected: 0 }
    }
}

// ── Setup wizard state ───────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
pub enum SetupField {
    Model,
    Done,
}

#[derive(Debug, Clone)]
pub struct SetupState {
    #[allow(dead_code)]
    pub field: SetupField,
    pub model_buf: String,
    pub error: Option<String>,
}

// ── Screen ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub enum Screen {
    Setup(SetupState),
    Chat,
}

// ── Actions ──────────────────────────────────────────────────────────────────

pub enum Action {
    WsConnected,
    WsDisconnected,
    WsEvent(WsEvent),
    SendMessage(String),
    ScrollUp,
    ScrollDown,
    ScrollToBottom,
    ToggleThinking { msg: usize, part: usize },
    ToggleTool { msg: usize, part: usize },
    SetupNext,
    SetupModelInput(String),
    Quit,
    Tick,
    PopupUp,
    PopupDown,
    PopupClose,
    CommandClear,
    CommandSetModel(String),
    CommandSetSystem(String),
    CommandHelp,
    CommandExport,
}

// ── App ──────────────────────────────────────────────────────────────────────

pub struct App {
    pub screen: Screen,
    pub config: Config,
    pub messages: Vec<ChatMessage>,
    /// Offset from the bottom (0 = auto-scroll to bottom).
    pub scroll_offset: usize,
    pub conn_status: ConnStatus,
    pub should_quit: bool,
    pub token_counts: (u32, u32),
    pub current_dir: String,
    pub tick: u64,
    pub command_popup: Option<CommandPopupState>,
    /// Chat history in the wire format the Python backend expects.
    pub history: Vec<Value>,
}

impl App {
    pub fn new(config: Config) -> Self {
        let needs_setup = !Config::has_api_key();
        let screen = if needs_setup {
            Screen::Setup(SetupState {
                field: SetupField::Model,
                model_buf: config.model.clone(),
                error: None,
            })
        } else {
            Screen::Chat
        };
        Self {
            screen,
            config,
            messages: Vec::new(),
            scroll_offset: 0,
            conn_status: ConnStatus::Connecting,
            should_quit: false,
            token_counts: (0, 0),
            current_dir: std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| "~".to_string()),
            tick: 0,
            command_popup: None,
            history: Vec::new(),
        }
    }

    pub fn update(&mut self, action: Action) {
        match action {
            Action::WsConnected => self.conn_status = ConnStatus::Connected,
            Action::WsDisconnected => self.conn_status = ConnStatus::Disconnected,
            Action::WsEvent(ev) => self.handle_ws_event(ev),

            Action::SendMessage(text) => {
                // Record in wire-format history (will be updated when response completes)
                let user_entry = serde_json::json!({ "role": "user", "content": text });
                self.history.push(user_entry);
                self.messages.push(ChatMessage::User(text));
                self.messages.push(ChatMessage::Assistant {
                    parts: Vec::new(),
                    done: false,
                });
                self.scroll_offset = 0; // auto-scroll to bottom
            }

            Action::ScrollUp => {
                self.scroll_offset += 3;
            }
            Action::ScrollDown => {
                self.scroll_offset = self.scroll_offset.saturating_sub(3);
            }
            Action::ScrollToBottom => {
                self.scroll_offset = 0;
            }

            Action::ToggleThinking { msg, part } => {
                if let Some(ChatMessage::Assistant { parts, .. }) = self.messages.get_mut(msg) {
                    if let Some(AssistantPart::Thinking { expanded, .. }) = parts.get_mut(part) {
                        *expanded = !*expanded;
                    }
                }
            }
            Action::ToggleTool { msg, part } => {
                if let Some(ChatMessage::Assistant { parts, .. }) = self.messages.get_mut(msg) {
                    if let Some(AssistantPart::ToolCall { expanded, .. }) = parts.get_mut(part) {
                        *expanded = !*expanded;
                    }
                }
            }

            Action::SetupModelInput(s) => {
                if let Screen::Setup(ref mut st) = self.screen {
                    st.model_buf = s;
                }
            }
            Action::SetupNext => {
                if let Screen::Setup(ref st) = self.screen.clone() {
                    let model = st.model_buf.trim().to_string();
                    if model.is_empty() {
                        if let Screen::Setup(ref mut st) = self.screen {
                            st.error = Some("Model name cannot be empty.".into());
                        }
                        return;
                    }
                    self.config.model = model;
                    let _ = self.config.save();
                    self.screen = Screen::Chat;
                }
            }

            Action::Quit => self.should_quit = true,

            Action::Tick => self.tick = self.tick.wrapping_add(1),

            Action::PopupUp => {
                if let Some(ref mut p) = self.command_popup {
                    if p.selected > 0 { p.selected -= 1; }
                }
            }
            Action::PopupDown => {
                if let Some(ref mut p) = self.command_popup {
                    p.selected += 1;
                }
            }
            Action::PopupClose => self.command_popup = None,

            Action::CommandClear => {
                self.messages.clear();
                self.history.clear();
                self.scroll_offset = 0;
                self.command_popup = None;
            }
            Action::CommandSetModel(m) => {
                self.config.model = m;
                let _ = self.config.save();
                self.command_popup = None;
            }
            Action::CommandSetSystem(_s) => {
                // System prompt not persisted yet — future work
                self.command_popup = None;
            }
            Action::CommandHelp => {
                self.messages.push(ChatMessage::Assistant {
                    parts: vec![AssistantPart::Text(
                        "**Commands**\n\n\
                         `/model <name>` — 切换模型\n\
                         `/clear` — 清空会话\n\
                         `/system <text>` — 设置 system prompt\n\
                         `/help` — 显示此帮助\n\
                         `/export` — 导出会话为 JSON\n\n\
                         **Keys:** `↑/↓` scroll · `Ctrl+O` toggle thinking · `Ctrl+C` quit"
                        .to_string(),
                    )],
                    done: true,
                });
                self.command_popup = None;
            }
            Action::CommandExport => {
                let filename = format!(
                    "proteinclaw-session-{}.json",
                    std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_secs()
                );
                let _ = std::fs::write(&filename, serde_json::to_string_pretty(&self.history).unwrap_or_default());
                self.command_popup = None;
            }
        }
    }

    fn handle_ws_event(&mut self, event: WsEvent) {
        let last = self.messages.last_mut();
        match event {
            WsEvent::Token { content } => {
                if let Some(ChatMessage::Assistant { parts, .. }) = last {
                    match parts.last_mut() {
                        Some(AssistantPart::Text(t)) => t.push_str(&content),
                        _ => parts.push(AssistantPart::Text(content)),
                    }
                }
            }

            WsEvent::Thinking { content } => {
                if let Some(ChatMessage::Assistant { parts, .. }) = last {
                    match parts.last_mut() {
                        Some(AssistantPart::Thinking { content: c, .. }) => {
                            c.push_str(&content)
                        }
                        _ => parts.push(AssistantPart::Thinking {
                            content,
                            expanded: false,
                        }),
                    }
                }
            }

            WsEvent::ToolCall { tool, args } => {
                if let Some(ChatMessage::Assistant { parts, .. }) = last {
                    parts.push(AssistantPart::ToolCall {
                        tool,
                        args,
                        result: None,
                        expanded: false,
                    });
                }
            }

            WsEvent::Observation { result, .. } => {
                if let Some(ChatMessage::Assistant { parts, .. }) = last {
                    for part in parts.iter_mut().rev() {
                        if let AssistantPart::ToolCall {
                            result: r, ..
                        } = part
                        {
                            if r.is_none() {
                                *r = Some(
                                    serde_json::to_string_pretty(&result)
                                        .unwrap_or_else(|_| result.to_string()),
                                );
                                break;
                            }
                        }
                    }
                }
            }

            WsEvent::TokenUsage { input_tokens, output_tokens } => {
                self.token_counts = (input_tokens, output_tokens);
            }

            WsEvent::Done => {
                if let Some(ChatMessage::Assistant { parts, done }) = last {
                    *done = true;
                    // Build assistant history entry from text parts
                    let text: String = parts
                        .iter()
                        .filter_map(|p| {
                            if let AssistantPart::Text(t) = p {
                                Some(t.as_str())
                            } else {
                                None
                            }
                        })
                        .collect();
                    self.history
                        .push(serde_json::json!({ "role": "assistant", "content": text }));
                }
            }

            WsEvent::Error { message } => {
                // Remove empty pending assistant slot
                if matches!(
                    self.messages.last(),
                    Some(ChatMessage::Assistant { parts, .. }) if parts.is_empty()
                ) {
                    self.messages.pop();
                }
                self.messages.push(ChatMessage::Error(message));
            }
        }
    }

    /// Returns (message_index, part_index) for every collapsible part,
    /// so the key handler can find what to toggle.
    pub fn collapsible_parts(&self) -> Vec<(usize, usize)> {
        let mut out = Vec::new();
        for (mi, msg) in self.messages.iter().enumerate() {
            if let ChatMessage::Assistant { parts, .. } = msg {
                for (pi, part) in parts.iter().enumerate() {
                    match part {
                        AssistantPart::Thinking { .. } | AssistantPart::ToolCall { .. } => {
                            out.push((mi, pi));
                        }
                        _ => {}
                    }
                }
            }
        }
        out
    }
}
