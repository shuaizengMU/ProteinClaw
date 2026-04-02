mod app;
mod config;
mod events;
mod server;
mod ui;
mod widgets;
mod ws;

use anyhow::Result;
use app::{Action, App, Screen};
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
    style_textarea(&mut textarea, false);

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
    // Scroll (vim-style + arrows)
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
            // gg = scroll to bottom (single g resets for now)
            app.update(Action::ScrollToBottom);
            return;
        }
        (KeyModifiers::CONTROL, KeyCode::Char('o')) => {
            // Toggle the most recent collapsible part
            let parts = app.collapsible_parts();
            if let Some((mi, pi)) = parts.last().copied() {
                // Determine type by checking the part
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

    // Enter → send message (plain Enter; Shift+Enter is passed to textarea)
    if key.modifiers == KeyModifiers::NONE && key.code == KeyCode::Enter {
        let text: String = textarea.lines().join("\n").trim().to_string();
        if !text.is_empty() {
            // Reset textarea
            *textarea = TextArea::default();
            textarea.set_placeholder_text(
                "Message ProteinClaw…  (Enter to send, Shift+Enter for newline)",
            );
            style_textarea(textarea, false);

            // Send to WS
            let history = app.history.clone();
            let model = app.config.model.clone();
            let _ = ws::send_message(cmd_tx, text.clone(), history, model);
            app.update(Action::SendMessage(text));
        }
        return;
    }

    // All other keys → forward to textarea
    textarea.input(key);
    style_textarea(textarea, !textarea.is_empty());
}

fn handle_setup_key(key: event::KeyEvent, app: &mut App) {
    if let Screen::Setup(_) = &app.screen {
        match key.code {
            KeyCode::Enter => app.update(Action::SetupNext),
            KeyCode::Char(c) => {
                if let Screen::Setup(ref st) = app.screen.clone() {
                    let mut buf = st.model_buf.clone();
                    buf.push(c);
                    app.update(Action::SetupModelInput(buf));
                }
            }
            KeyCode::Backspace => {
                if let Screen::Setup(ref st) = app.screen.clone() {
                    let mut buf = st.model_buf.clone();
                    buf.pop();
                    app.update(Action::SetupModelInput(buf));
                }
            }
            _ => {}
        }
    }
}

// ── Textarea styling ──────────────────────────────────────────────────────────

fn style_textarea(textarea: &mut TextArea, has_content: bool) {
    use ratatui::{
        style::{Color, Style},
        widgets::{Block, Borders},
    };
    let border_color = if has_content {
        Color::Cyan
    } else {
        Color::DarkGray
    };
    textarea.set_block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(border_color))
            .title(" Message (Enter → send  Shift+Enter → newline  Ctrl+C → quit) "),
    );
    textarea.set_cursor_line_style(Style::default());
}
