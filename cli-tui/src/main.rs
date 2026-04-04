mod app;
mod config;
mod copilot_auth;
mod events;
mod server;
mod ui;
mod widgets;
mod ws;
mod registry;

use anyhow::Result;
use app::{Action, App, Screen, SetupState, SetupStep, WizardMode};
use config::Config;
use crossterm::{
    event::{
        self, Event as CEvent, KeyCode, KeyEventKind,
        KeyModifiers,
    },
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::time::Duration;
use tokio::sync::mpsc;
use tui_textarea::TextArea;
use ws::{WsAppEvent, WsCmd};

#[tokio::main]
async fn main() -> Result<()> {
    // ── Config ───────────────────────────────────────────────────────────────
    let config = Config::load().unwrap_or_default();

    // ── Python server ────────────────────────────────────────────────────────
    let _server = server::spawn(config.server_port)?;
    server::wait_ready(config.server_port).await?;

    // ── WebSocket channels ───────────────────────────────────────────────────
    let (event_tx, mut event_rx) = mpsc::unbounded_channel::<WsAppEvent>();
    let (cmd_tx, cmd_rx) = mpsc::unbounded_channel::<WsCmd>();
    tokio::spawn(ws::run(config.server_port, event_tx, cmd_rx));

    // ── Action channel (for background tasks to send actions to the main loop) ─
    let (action_tx, mut action_rx) = mpsc::unbounded_channel::<Action>();

    // ── App state ────────────────────────────────────────────────────────────
    let mut app = App::new(config);

    // ── Input textarea ───────────────────────────────────────────────────────
    let mut textarea = TextArea::default();
    textarea.set_placeholder_text("Message ProteinClaw…  (Enter to send, Shift+Enter for newline)");
    widgets::input::apply_style(&mut textarea);

    // ── Terminal ─────────────────────────────────────────────────────────────
    enable_raw_mode()?;
    let mut stdout = std::io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let tick = Duration::from_millis(50);

    loop {
        // Draw
        terminal.draw(|f| ui::draw(f, &app, &textarea))?;

        // Drain WS events (non-blocking)
        while let Ok(ev) = event_rx.try_recv() {
            match ev {
                WsAppEvent::Connected => app.update(Action::WsConnected),
                WsAppEvent::Disconnected => app.update(Action::WsDisconnected),
                WsAppEvent::Event(ws_ev) => app.update(Action::WsEvent(ws_ev)),
                WsAppEvent::Error(msg) => {
                    app.update(Action::WsEvent(crate::events::WsEvent::Error {
                        message: msg,
                    }))
                }
            }
        }

        // Drain actions from background tasks
        while let Ok(action) = action_rx.try_recv() {
            app.update(action);
        }

        // Kick off GitHub Copilot device-flow when we enter the login screen
        if let Screen::Setup(ref st) = app.screen {
            if let app::SetupStep::GitHubLogin { ref user_code, .. } = st.step {
                if user_code.is_empty() && !app.github_auth_running {
                    app.github_auth_running = true;
                    let tx = action_tx.clone();
                    tokio::spawn(async move {
                        match copilot_auth::request_device_code().await {
                            Ok(dc) => {
                                let device_code = dc.device_code.clone();
                                let interval = dc.interval;
                                let _ = tx.send(Action::GitHubDeviceCode {
                                    user_code: dc.user_code,
                                    verification_uri: dc.verification_uri,
                                });
                                // Poll for OAuth token — save it directly;
                                // the Python backend exchanges it for a session token on each request.
                                match copilot_auth::poll_for_token(&device_code, interval).await {
                                    Ok(oauth_token) => {
                                        let _ = tx.send(Action::GitHubLoginDone(oauth_token));
                                    }
                                    Err(e) => {
                                        let _ = tx.send(Action::GitHubLoginError(e.to_string()));
                                    }
                                }
                            }
                            Err(e) => {
                                let _ = tx.send(Action::GitHubLoginError(e.to_string()));
                            }
                        }
                    });
                }
            }
        }
        // Reset the flag when we leave the GitHub login screen
        if !matches!(&app.screen, Screen::Setup(st) if matches!(st.step, app::SetupStep::GitHubLogin { .. }))
        {
            app.github_auth_running = false;
        }

        app.update(Action::Tick);

        // Poll keyboard / terminal events
        if event::poll(tick)? {
            match event::read()? {
                CEvent::Key(key) => {
                    // Only process key-press events (ignore key-release on Windows)
                    if key.kind != KeyEventKind::Press {
                        continue;
                    }

                    // Ctrl+C: first press = cancel/clear, second press within 2s = quit
                    if key.modifiers == KeyModifiers::CONTROL && key.code == KeyCode::Char('c') {
                        let now = std::time::Instant::now();
                        if let Some(prev) = app.ctrl_c_at {
                            if now.duration_since(prev).as_secs() < 2 {
                                app.update(Action::Quit);
                                continue;
                            }
                        }
                        // First press: record time, clear input
                        app.ctrl_c_at = Some(now);
                        textarea = TextArea::default();
                        textarea.set_placeholder_text(
                            "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
                        );
                        widgets::input::apply_style(&mut textarea);
                        app.command_popup = None;
                        continue;
                    }

                    // Any other key resets the Ctrl+C state
                    app.ctrl_c_at = None;

                    match &app.screen {
                        Screen::Chat => handle_chat_key(key, &mut app, &mut textarea, &cmd_tx),
                        Screen::Setup(_) => handle_setup_key(key, &mut app),
                    }
                }
                _ => {}
            }
        }

        if app.should_quit {
            break;
        }
    }

    // ── Restore terminal ─────────────────────────────────────────────────────
    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    Ok(())
}

// ── Key handlers ─────────────────────────────────────────────────────────────

fn handle_chat_key(
    key: event::KeyEvent,
    app: &mut App,
    textarea: &mut TextArea,
    cmd_tx: &mpsc::UnboundedSender<WsCmd>,
) {
    use crate::widgets::command_popup::filtered_entries;

    // ── Command popup navigation ─────────────────────────────────────────────
    if app.command_popup.is_some() {
        match (key.modifiers, key.code) {
            (KeyModifiers::NONE, KeyCode::Esc) => {
                app.update(Action::PopupClose);
                return;
            }
            (KeyModifiers::NONE, KeyCode::Up) => {
                app.update(Action::PopupUp);
                return;
            }
            (KeyModifiers::NONE, KeyCode::Down) => {
                app.update(Action::PopupDown);
                return;
            }
            (KeyModifiers::NONE, KeyCode::Enter) => {
                if let Some(ref popup) = app.command_popup {
                    let entries = filtered_entries(&popup.filter);
                    let idx = popup.selected.min(entries.len().saturating_sub(1));
                    if let Some(entry) = entries.get(idx) {
                        if let Some((pi, mi)) = entry.model {
                            // Model entry — select model (checks API key internally)
                            *textarea = TextArea::default();
                            textarea.set_placeholder_text(
                                "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
                            );
                            widgets::input::apply_style(textarea);
                            app.update(Action::SelectModel { provider_idx: pi, model_idx: mi });
                        } else {
                            // Command entry — fill into textarea
                            *textarea = TextArea::default();
                            textarea.set_placeholder_text(
                                "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
                            );
                            widgets::input::apply_style(textarea);
                            for ch in entry.display.chars() {
                                textarea.insert_char(ch);
                            }
                            app.update(Action::PopupClose);
                        }
                    }
                }
                return;
            }
            _ => {
                // While popup is open forward key to textarea for filter input,
                // but skip scroll handlers below.
                textarea.input(key);
                widgets::input::apply_style(textarea);
                let first_line = textarea.lines().first().map(|s| s.as_str()).unwrap_or("").to_string();
                if first_line.starts_with('/') {
                    let filter = first_line[1..].to_string();
                    if let Some(ref mut p) = app.command_popup {
                        p.filter = filter;
                        let max = crate::widgets::command_popup::filtered_entries(&p.filter)
                            .len()
                            .saturating_sub(1);
                        p.selected = p.selected.min(max);
                    }
                } else {
                    app.command_popup = None;
                }
                return;
            }
        }
    }

    // ── Scroll (arrows only — letter keys must reach the textarea) ──────────
    match (key.modifiers, key.code) {
        (KeyModifiers::NONE, KeyCode::Up) => {
            app.update(Action::ScrollUp);
            return;
        }
        (KeyModifiers::NONE, KeyCode::Down) => {
            app.update(Action::ScrollDown);
            return;
        }
        (KeyModifiers::CONTROL, KeyCode::Char('r')) => {
            if app.auth_error {
                app.update(Action::OpenApiKeySetup);
            }
            return;
        }
        (KeyModifiers::CONTROL, KeyCode::Char('o')) => {
            let parts = app.collapsible_parts();
            if let Some((mi, pi)) = parts.last().copied() {
                if let Some(crate::app::ChatMessage::Assistant { parts: p, .. }) =
                    app.messages.get(mi)
                {
                    match p.get(pi) {
                        Some(crate::app::AssistantPart::Thinking { .. }) => {
                            app.update(Action::ToggleThinking { msg: mi, part: pi });
                        }
                        Some(crate::app::AssistantPart::ToolCall { .. }) => {
                            app.update(Action::ToggleTool { msg: mi, part: pi });
                        }
                        _ => {}
                    }
                }
            }
            return;
        }
        _ => {}
    }

    // ── Enter → execute command or send message ──────────────────────────────
    if key.modifiers == KeyModifiers::NONE && key.code == KeyCode::Enter {
        let text: String = textarea.lines().join("\n").trim().to_string();
        if !text.is_empty() {
            *textarea = TextArea::default();
            textarea.set_placeholder_text(
                "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
            );
            widgets::input::apply_style(textarea);
            app.command_popup = None;

            if text.starts_with('/') {
                let (cmd, rest) = text.split_once(' ').unwrap_or((&text, ""));
                match cmd {
                    "/clear"  => { app.update(Action::CommandClear); }
                    "/help"   => { app.update(Action::CommandHelp); }
                    "/export" => { app.update(Action::CommandExport); }
                    "/demo"   => { app.update(Action::CommandDemo); }
                    "/copy"   => { app.update(Action::CommandCopy); }
                    "/model"  => {
                        let model = rest.trim().to_string();
                        if !model.is_empty() {
                            app.update(Action::CommandSetModel(model));
                        } else {
                            app.screen = Screen::Setup(SetupState {
                                step: SetupStep::Provider,
                                provider_idx: 0,
                                model_idx: 0,
                                key_buf: String::new(),
                                error: None,
                                mode: WizardMode::SwitchModel,
                            });
                            app.command_popup = None;
                        }
                    }
                    "/system" => {
                        let sys = rest.trim().to_string();
                        if !sys.is_empty() {
                            app.update(Action::CommandSetSystem(sys));
                        }
                    }
                    _ => {
                        app.messages.push(crate::app::ChatMessage::Error(
                            format!("Unknown command: {}. Type /help for a list.", cmd),
                        ));
                    }
                }
                return;
            }

            let history = app.history.clone();
            let model = app.config.model.clone();
            let _ = ws::send_message(cmd_tx, text.clone(), history, model);
            app.update(Action::SendMessage(text));
        }
        return;
    }

    // ── All other keys → forward to textarea ────────────────────────────────
    textarea.input(key);
    widgets::input::apply_style(textarea);

    // Sync command popup with current input
    let first_line = textarea.lines().first().map(|s| s.as_str()).unwrap_or("").to_string();
    if first_line.starts_with('/') {
        let filter = first_line[1..].to_string();
        match app.command_popup {
            None => {
                app.command_popup = Some(crate::app::CommandPopupState { filter, selected: 0 });
            }
            Some(ref mut p) => {
                p.filter = filter;
                let max = crate::widgets::command_popup::filtered_entries(&p.filter)
                    .len()
                    .saturating_sub(1);
                p.selected = p.selected.min(max);
            }
        }
    } else {
        app.command_popup = None;
    }
}

fn handle_setup_key(key: event::KeyEvent, app: &mut App) {
    if let Screen::Setup(ref st) = app.screen {
        match st.step {
            app::SetupStep::Provider | app::SetupStep::Model => {
                match key.code {
                    KeyCode::Up => app.update(Action::SetupUp),
                    KeyCode::Down => app.update(Action::SetupDown),
                    KeyCode::Enter => app.update(Action::SetupNext),
                    KeyCode::Esc => app.update(Action::SetupBack),
                    _ => {}
                }
            }
            app::SetupStep::ApiKey => {
                match key.code {
                    KeyCode::Enter => app.update(Action::SetupNext),
                    KeyCode::Esc => app.update(Action::SetupBack),
                    KeyCode::Char(c) => {
                        let mut buf = st.key_buf.clone();
                        buf.push(c);
                        app.update(Action::SetupKeyInput(buf));
                    }
                    KeyCode::Backspace => {
                        let mut buf = st.key_buf.clone();
                        buf.pop();
                        app.update(Action::SetupKeyInput(buf));
                    }
                    _ => {}
                }
            }
            app::SetupStep::GitHubLogin { .. } => {
                match key.code {
                    KeyCode::Esc => app.update(Action::SetupBack),
                    _ => {}
                }
            }
        }
    }
}

