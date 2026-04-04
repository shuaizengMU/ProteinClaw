use crate::config::Config;
use crate::events::WsEvent;
use serde_json::Value;
use std::time::Instant;

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
    Assistant { parts: Vec<AssistantPart>, done: bool, elapsed: Option<u64> },
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
pub enum SetupStep {
    Provider,
    Model,
    ApiKey,
    /// GitHub Copilot device-flow login.
    GitHubLogin {
        user_code: String,
        verification_uri: String,
        status: String,
    },
}

#[derive(Debug, Clone, PartialEq)]
pub enum WizardMode {
    FirstRun,
    SwitchModel,
}

#[derive(Debug, Clone)]
pub struct SetupState {
    pub step: SetupStep,
    pub provider_idx: usize,
    pub model_idx: usize,
    pub key_buf: String,
    pub error: Option<String>,
    pub mode: WizardMode,
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
    SetupUp,
    SetupDown,
    SetupNext,
    SetupBack,
    SetupKeyInput(String),
    Quit,
    Tick,
    PopupUp,
    PopupDown,
    PopupClose,
    CommandClear,
    CommandSetModel(String),
    /// User picked a model from the popup dropdown (provider_idx, model_idx).
    SelectModel { provider_idx: usize, model_idx: usize },
    CommandSetSystem(String),
    CommandHelp,
    CommandExport,
    CommandDemo,
    CommandCopy,
    OpenApiKeySetup,
    /// GitHub Copilot device-flow: show the user code and verification URI.
    GitHubDeviceCode {
        user_code: String,
        verification_uri: String,
    },
    /// GitHub Copilot device-flow completed — store the token.
    GitHubLoginDone(String),
    /// GitHub Copilot device-flow failed.
    GitHubLoginError(String),
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
    /// Start time of the current in-flight request, for elapsed timing.
    pub pending_start: Option<Instant>,
    /// True when the last error was an authentication failure.
    pub auth_error: bool,
    /// True while the GitHub device-flow background task is running.
    pub github_auth_running: bool,
    /// Set when the user presses Ctrl+C once; a second press within this window quits.
    pub ctrl_c_at: Option<Instant>,
}

impl App {
    pub fn new(config: Config) -> Self {
        let needs_setup = !Config::has_api_key();
        let screen = if needs_setup {
            Screen::Setup(SetupState {
                step: SetupStep::Provider,
                provider_idx: 0,
                model_idx: 0,
                key_buf: String::new(),
                error: None,
                mode: WizardMode::FirstRun,
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
            auth_error: false,
            github_auth_running: false,
            ctrl_c_at: None,
            pending_start: None,
        }
    }

    pub fn update(&mut self, action: Action) {
        match action {
            Action::WsConnected => self.conn_status = ConnStatus::Connected,
            Action::WsDisconnected => self.conn_status = ConnStatus::Disconnected,
            Action::WsEvent(ev) => self.handle_ws_event(ev),

            Action::SendMessage(text) => {
                self.auth_error = false;
                // Record in wire-format history (will be updated when response completes)
                let user_entry = serde_json::json!({ "role": "user", "content": text });
                self.history.push(user_entry);
                self.messages.push(ChatMessage::User(text));
                self.messages.push(ChatMessage::Assistant {
                    parts: Vec::new(),
                    done: false,
                    elapsed: None,
                });
                self.pending_start = Some(Instant::now());
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

            Action::SetupUp => {
                if let Screen::Setup(ref mut st) = self.screen {
                    match st.step {
                        SetupStep::Provider => {
                            st.provider_idx = st.provider_idx.saturating_sub(1);
                        }
                        SetupStep::Model => {
                            st.model_idx = st.model_idx.saturating_sub(1);
                        }
                        SetupStep::ApiKey | SetupStep::GitHubLogin { .. } => {}
                    }
                    st.error = None;
                }
            }
            Action::SetupDown => {
                if let Screen::Setup(ref mut st) = self.screen {
                    match st.step {
                        SetupStep::Provider => {
                            let max = crate::registry::PROVIDERS.len().saturating_sub(1);
                            st.provider_idx = (st.provider_idx + 1).min(max);
                        }
                        SetupStep::Model => {
                            let provider = &crate::registry::PROVIDERS[st.provider_idx];
                            let max = provider.models.len().saturating_sub(1);
                            st.model_idx = (st.model_idx + 1).min(max);
                        }
                        SetupStep::ApiKey | SetupStep::GitHubLogin { .. } => {}
                    }
                    st.error = None;
                }
            }
            Action::SetupNext => {
                if let Screen::Setup(ref st) = self.screen.clone() {
                    let provider = &crate::registry::PROVIDERS[st.provider_idx];
                    match st.step {
                        SetupStep::Provider => {
                            if let Screen::Setup(ref mut st) = self.screen {
                                st.step = SetupStep::Model;
                                st.model_idx = 0;
                                st.error = None;
                            }
                        }
                        SetupStep::Model => {
                            let is_copilot = provider.name == "GitHub Copilot";
                            let key_already_set = !provider.env_var.is_empty()
                                && std::env::var(provider.env_var)
                                    .map(|v| !v.is_empty())
                                    .unwrap_or(false);
                            let skip_key = provider.env_var.is_empty() || key_already_set;

                            if skip_key {
                                let model = provider.models[st.model_idx].name.to_string();
                                self.config.model = model;
                                let _ = self.config.save();
                                self.screen = Screen::Chat;
                            } else if is_copilot {
                                // GitHub Copilot uses device-flow login, not a manual API key.
                                if let Screen::Setup(ref mut st) = self.screen {
                                    st.step = SetupStep::GitHubLogin {
                                        user_code: String::new(),
                                        verification_uri: String::new(),
                                        status: "Requesting device code...".into(),
                                    };
                                    st.error = None;
                                }
                            } else {
                                if let Screen::Setup(ref mut st) = self.screen {
                                    st.step = SetupStep::ApiKey;
                                    st.key_buf.clear();
                                    st.error = None;
                                }
                            }
                        }
                        SetupStep::ApiKey => {
                            let key = st.key_buf.trim().to_string();
                            if key.is_empty() {
                                if let Screen::Setup(ref mut st) = self.screen {
                                    st.error = Some("API key cannot be empty.".into());
                                }
                                return;
                            }
                            let model = provider.models[st.model_idx].name.to_string();
                            let env_var = provider.env_var.to_string();
                            self.config.model = model;
                            std::env::set_var(&env_var, &key);
                            let _ = self.config.save_with_key(&env_var, &key);
                            self.screen = Screen::Chat;
                        }
                        SetupStep::GitHubLogin { .. } => {
                            // No manual action — polling happens in the background.
                        }
                    }
                }
            }
            Action::SetupBack => {
                let mode = if let Screen::Setup(ref st) = self.screen {
                    st.mode.clone()
                } else {
                    return;
                };
                if let Screen::Setup(ref mut st) = self.screen {
                    match st.step {
                        SetupStep::Provider => {
                            if mode == WizardMode::SwitchModel {
                                self.screen = Screen::Chat;
                            }
                            // FirstRun: no-op
                        }
                        SetupStep::Model => {
                            st.step = SetupStep::Provider;
                            st.error = None;
                        }
                        SetupStep::ApiKey | SetupStep::GitHubLogin { .. } => {
                            st.step = SetupStep::Model;
                            st.error = None;
                        }
                    }
                }
            }
            Action::SetupKeyInput(s) => {
                if let Screen::Setup(ref mut st) = self.screen {
                    st.key_buf = s;
                    st.error = None;
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
                    // No upper bound here — the widget (command_popup.rs) clamps
                    // selected against filtered_commands().len() before rendering.
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
            Action::SelectModel { provider_idx, model_idx } => {
                let provider = &crate::registry::PROVIDERS[provider_idx];
                let model = provider.models[model_idx].name.to_string();
                let has_key = provider.env_var.is_empty()
                    || std::env::var(provider.env_var)
                        .map(|v| !v.is_empty())
                        .unwrap_or(false);

                self.command_popup = None;
                if has_key {
                    // API key already present — just switch model
                    self.config.model = model;
                    let _ = self.config.save();
                } else if provider.name == "GitHub Copilot" {
                    // Copilot requires device-flow login, not a manual API key.
                    self.screen = Screen::Setup(SetupState {
                        step: SetupStep::GitHubLogin {
                            user_code: String::new(),
                            verification_uri: String::new(),
                            status: "Starting GitHub login...".into(),
                        },
                        provider_idx,
                        model_idx,
                        key_buf: String::new(),
                        error: None,
                        mode: WizardMode::SwitchModel,
                    });
                } else {
                    // Need API key — open setup wizard at ApiKey step
                    self.screen = Screen::Setup(SetupState {
                        step: SetupStep::ApiKey,
                        provider_idx,
                        model_idx,
                        key_buf: String::new(),
                        error: None,
                        mode: WizardMode::SwitchModel,
                    });
                }
            }
            Action::CommandSetSystem(_s) => {
                self.messages.push(ChatMessage::Assistant {
                    parts: vec![AssistantPart::Text(
                        "System prompt support is not yet implemented.".to_string(),
                    )],
                    done: true,
                    elapsed: None,
                });
                self.command_popup = None;
            }
            Action::CommandHelp => {
                self.messages.push(ChatMessage::Assistant {
                    parts: vec![AssistantPart::Text(
                        "**Commands**\n\n\
                         `/model <name>` — Switch model\n\
                         `/clear` — Clear session\n\
                         `/system <text>` — Set system prompt\n\
                         `/help` — Show this help\n\
                         `/export` — Export session as JSON\n\
                         `/demo` — Show available use case examples\n\
                         `/copy` — Copy last response to clipboard\n\n\
                         **Keys:** `↑/↓` scroll · `Ctrl+O` toggle thinking · `Ctrl+C` quit\n\
                         **Tip:** Hold `Shift` + mouse drag to select and copy text"
                        .to_string(),
                    )],
                    done: true,
                    elapsed: None,
                });
                self.command_popup = None;
            }
            Action::CommandDemo => {
                self.messages.push(ChatMessage::Assistant {
                    parts: vec![AssistantPart::Text(
                        "**Use Case Examples**\n\n\
                         Here are things ProteinClaw can help you with — feel free to copy and ask:\n\n\
                         **Protein Information Lookup**\n\
                         • `Look up basic info and function of P53 protein (P04637)`\n\
                         • `What are the known domains of human insulin (P01308)?`\n\n\
                         **Sequence Analysis**\n\
                         • `Analyze the physicochemical properties of this sequence: MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH`\n\
                         • `BLAST this sequence and find homologous proteins: MKWVTFISLLFLFSSAYS...`\n\n\
                         **Structure & Function**\n\
                         • `Show details of PDB structure 4HHB`\n\
                         • `Is there an AlphaFold predicted structure for P04637?`\n\n\
                         **Pathways & Interaction Networks**\n\
                         • `Which KEGG signaling pathways does TP53 participate in?`\n\
                         • `Query the protein interaction network of TP53 (STRING)`\n\
                         • `What Reactome pathways involve BRCA1?`\n\n\
                         **Disease & Clinical**\n\
                         • `What diseases are associated with BRCA1? (OMIM)`\n\
                         • `Search ClinVar for clinical variants in CFTR`\n\
                         • `Find disease-gene associations for TP53 (DisGeNET)`\n\n\
                         **Drug Discovery**\n\
                         • `What drugs target EGFR? (ChEMBL)`\n\
                         • `Find approved drugs and clinical candidates for ALK`\n\n\
                         **Genomics & Evolution**\n\
                         • `Get Ensembl genomic info and orthologs for BRCA2`\n\
                         • `Look up NCBI Gene info for TP53`\n\n\
                         **Post-Translational Modifications**\n\
                         • `What PTM sites are annotated for P04637? (PhosphoSite)`\n\
                         • `Predict signal peptide and TM helices for this sequence (ExPASy)`\n\n\
                         **Function Classification**\n\
                         • `What are the GO annotations for P04637? (Gene Ontology)`\n\
                         • `Classify TP53 into PANTHER protein families`\n\n\
                         **Target Validation & Population Genetics**\n\
                         • `What diseases are associated with EGFR? (Open Targets)`\n\
                         • `Find GWAS associations for BRCA1`\n\n\
                         **Expression & Localization**\n\
                         • `Where is TP53 expressed in human tissues? (Human Protein Atlas)`\n\n\
                         **Curated Interactions**\n\
                         • `Find curated molecular interactions for P04637 (IntAct)`\n\n\
                         **Structural Classification**\n\
                         • `What CATH structural domains does P04637 have?`\n\n\
                         **Sequence Motifs**\n\
                         • `Predict short linear motifs in P04637 (ELM)`\n\n\
                         **Literature Search**\n\
                         • `Search for recent publications on CRISPR-Cas9 protein engineering`\n\
                         • `Find research papers related to P53 mutants`\n\n\
                         **Comprehensive Analysis**\n\
                         • `Comprehensive analysis of BRCA1: function, structure, interactions, and literature`\n\
                         • `Compare human and mouse hemoglobin alpha subunits — what are the differences?`\n\n\
                         Tip: You can ask in natural language — ProteinClaw will automatically invoke the right tools."
                        .to_string(),
                    )],
                    done: true,
                    elapsed: None,
                });
                self.command_popup = None;
            }
            Action::CommandCopy => {
                // Find the last assistant text response.
                let text = self.messages.iter().rev().find_map(|m| {
                    if let ChatMessage::Assistant { parts, done: true, .. } = m {
                        let t: String = parts.iter().filter_map(|p| {
                            if let AssistantPart::Text(s) = p { Some(s.as_str()) } else { None }
                        }).collect::<Vec<_>>().join("");
                        if !t.is_empty() { Some(t) } else { None }
                    } else {
                        None
                    }
                });
                if let Some(text) = text {
                    // Use OSC 52 escape sequence to copy to system clipboard.
                    // Supported by most modern terminals (iTerm2, kitty, WezTerm, etc.).
                    let b64 = base64_encode(&text);
                    let osc = format!("\x1b]52;c;{}\x07", b64);
                    let _ = std::io::Write::write_all(&mut std::io::stdout(), osc.as_bytes());
                    let _ = std::io::Write::flush(&mut std::io::stdout());
                    self.messages.push(ChatMessage::Assistant {
                        parts: vec![AssistantPart::Text("Copied to clipboard.".to_string())],
                        done: true,
                        elapsed: None,
                    });
                } else {
                    self.messages.push(ChatMessage::Error("No assistant response to copy.".to_string()));
                }
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
                let json = serde_json::to_string_pretty(&self.history).unwrap_or_default();
                match std::fs::write(&filename, json) {
                    Ok(()) => self.messages.push(ChatMessage::Assistant {
                        parts: vec![AssistantPart::Text(format!("Session exported to `{}`", filename))],
                        done: true,
                        elapsed: None,
                    }),
                    Err(e) => self.messages.push(ChatMessage::Error(format!("Export failed: {}", e))),
                }
                self.command_popup = None;
            }
            Action::OpenApiKeySetup => {
                // Find the provider for the current model
                let mut provider_idx = 0;
                let mut model_idx = 0;
                for (pi, provider) in crate::registry::PROVIDERS.iter().enumerate() {
                    for (mi, model) in provider.models.iter().enumerate() {
                        if self.config.model == model.name {
                            provider_idx = pi;
                            model_idx = mi;
                        }
                    }
                }
                let provider = &crate::registry::PROVIDERS[provider_idx];
                let is_copilot = provider.name == "GitHub Copilot";
                self.auth_error = false;
                if is_copilot {
                    self.screen = Screen::Setup(SetupState {
                        step: SetupStep::GitHubLogin {
                            user_code: String::new(),
                            verification_uri: String::new(),
                            status: "Requesting device code...".into(),
                        },
                        provider_idx,
                        model_idx,
                        key_buf: String::new(),
                        error: None,
                        mode: WizardMode::SwitchModel,
                    });
                } else {
                    self.screen = Screen::Setup(SetupState {
                        step: SetupStep::ApiKey,
                        provider_idx,
                        model_idx,
                        key_buf: String::new(),
                        error: None,
                        mode: WizardMode::SwitchModel,
                    });
                }
            }
            Action::GitHubDeviceCode { user_code, verification_uri } => {
                if let Screen::Setup(ref mut st) = self.screen {
                    st.step = SetupStep::GitHubLogin {
                        user_code,
                        verification_uri,
                        status: "Waiting for authorization...".into(),
                    };
                }
            }
            Action::GitHubLoginDone(oauth_token) => {
                // Only accept if the user is still on the GitHub login screen.
                if let Screen::Setup(ref st) = self.screen {
                    if matches!(st.step, SetupStep::GitHubLogin { .. }) {
                        let provider = &crate::registry::PROVIDERS[st.provider_idx];
                        let env_var = provider.env_var;
                        let model = provider.models[st.model_idx].name.to_string();
                        std::env::set_var(env_var, &oauth_token);
                        self.config.model = model;
                        let _ = self.config.save_with_key(env_var, &oauth_token);
                        self.screen = Screen::Chat;
                    }
                    // else: user navigated away — silently discard the stale token.
                }
                self.github_auth_running = false;
            }
            Action::GitHubLoginError(msg) => {
                if let Screen::Setup(ref mut st) = self.screen {
                    st.step = SetupStep::GitHubLogin {
                        user_code: String::new(),
                        verification_uri: String::new(),
                        status: format!("Error: {}", msg),
                    };
                    st.error = Some(msg);
                }
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
                if let Some(ChatMessage::Assistant { parts, done, elapsed }) = last {
                    *done = true;
                    if let Some(start) = self.pending_start.take() {
                        *elapsed = Some(start.elapsed().as_secs());
                    }
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
                let is_auth = message.contains("AuthenticationError")
                    || message.contains("401")
                    || message.contains("403")
                    || message.contains("Invalid API Key")
                    || message.contains("Incorrect API key");
                if is_auth {
                    self.auth_error = true;
                    self.messages.push(ChatMessage::Error(message));
                } else {
                    self.messages.push(ChatMessage::Error(message));
                }
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

/// Simple Base64 encoder (no external crate needed).
fn base64_encode(input: &str) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let bytes = input.as_bytes();
    let mut out = String::with_capacity((bytes.len() + 2) / 3 * 4);
    for chunk in bytes.chunks(3) {
        let b0 = chunk[0] as u32;
        let b1 = if chunk.len() > 1 { chunk[1] as u32 } else { 0 };
        let b2 = if chunk.len() > 2 { chunk[2] as u32 } else { 0 };
        let n = (b0 << 16) | (b1 << 8) | b2;
        out.push(TABLE[((n >> 18) & 0x3F) as usize] as char);
        out.push(TABLE[((n >> 12) & 0x3F) as usize] as char);
        if chunk.len() > 1 {
            out.push(TABLE[((n >> 6) & 0x3F) as usize] as char);
        } else {
            out.push('=');
        }
        if chunk.len() > 2 {
            out.push(TABLE[(n & 0x3F) as usize] as char);
        } else {
            out.push('=');
        }
    }
    out
}
