mod app;
mod config;
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
        self, DisableMouseCapture, EnableMouseCapture, Event as CEvent, KeyCode, KeyEventKind,
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

    // ── App state ────────────────────────────────────────────────────────────
    let mut app = App::new(config);

    // ── Input textarea ───────────────────────────────────────────────────────
    let mut textarea = TextArea::default();
    textarea.set_placeholder_text("Message ProteinClaw…  (Enter to send, Shift+Enter for newline)");
    widgets::input::apply_style(&mut textarea);

    // ── Terminal ─────────────────────────────────────────────────────────────
    enable_raw_mode()?;
    let mut stdout = std::io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
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

        app.update(Action::Tick);

        // Poll keyboard / terminal events
        if event::poll(tick)? {
            if let CEvent::Key(key) = event::read()? {
                // Only process key-press events (ignore key-release on Windows)
                if key.kind != KeyEventKind::Press {
                    continue;
                }

                // Quit
                if key.modifiers == KeyModifiers::CONTROL && key.code == KeyCode::Char('c') {
                    app.update(Action::Quit);
                }

                match &app.screen {
                    Screen::Chat => handle_chat_key(key, &mut app, &mut textarea, &cmd_tx),
                    Screen::Setup(_) => handle_setup_key(key, &mut app),
                }
            }
        }

        if app.should_quit {
            break;
        }
    }

    // ── Restore terminal ─────────────────────────────────────────────────────
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
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
    use crate::widgets::command_popup::filtered_commands;

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
                // Fill selected command into textarea
                if let Some(ref popup) = app.command_popup {
                    let cmds = filtered_commands(&popup.filter);
                    let idx = popup.selected.min(cmds.len().saturating_sub(1));
                    if let Some((cmd, _)) = cmds.get(idx) {
                        *textarea = TextArea::default();
                        textarea.set_placeholder_text(
                            "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
                        );
                        widgets::input::apply_style(textarea);
                        for ch in cmd.chars() {
                            textarea.insert_char(ch);
                        }
                    }
                }
                app.update(Action::PopupClose);
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
                        let max = crate::widgets::command_popup::filtered_commands(&p.filter)
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

    // ── Scroll (vim-style + arrows) ──────────────────────────────────────────
    match (key.modifiers, key.code) {
        (KeyModifiers::NONE, KeyCode::Up) | (KeyModifiers::NONE, KeyCode::Char('k')) => {
            app.update(Action::ScrollUp);
            return;
        }
        (KeyModifiers::NONE, KeyCode::Down) | (KeyModifiers::NONE, KeyCode::Char('j')) => {
            app.update(Action::ScrollDown);
            return;
        }
        (KeyModifiers::NONE, KeyCode::Char('g')) => {
            app.update(Action::ScrollToBottom);
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
                let max = crate::widgets::command_popup::filtered_commands(&p.filter)
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
        }
    }
}

