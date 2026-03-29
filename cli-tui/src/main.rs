mod app;
mod config;
mod events;
mod server;
mod views;
mod ws;

use std::io::stdout;
use std::time::Duration;

use crossterm::{
    event::{self, Event},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use tokio::sync::mpsc;

use app::App;
use events::AppEvent;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load config first — if setup is needed, we still start the server
    // so that MainView can use it immediately after setup completes.
    let cfg = config::load();

    // Start the Python backend server
    eprintln!("Starting ProteinClaw server...");
    let server = server::start().await.map_err(|e| {
        eprintln!("Error: {}", e);
        e
    })?;
    let port = server.port;
    eprintln!("Server ready on port {}", port);

    // Event channel shared between all producers
    let (event_tx, mut event_rx) = mpsc::channel::<AppEvent>(256);

    // Connect WebSocket
    let ws_tx = ws::connect(port, event_tx.clone()).await?;

    // Build app state
    let mut app = App::new(cfg, ws_tx);

    // Keyboard event producer
    let key_tx = event_tx.clone();
    tokio::task::spawn_blocking(move || {
        loop {
            if event::poll(Duration::from_millis(50)).unwrap_or(false) {
                match event::read() {
                    Ok(Event::Key(k)) => { let _ = key_tx.blocking_send(AppEvent::Key(k)); }
                    Ok(Event::Resize(w, h)) => { let _ = key_tx.blocking_send(AppEvent::Resize(w, h)); }
                    _ => {}
                }
            }
        }
    });

    // Set up terminal — restore on panic
    enable_raw_mode()?;
    let mut stdout = stdout();
    execute!(stdout, EnterAlternateScreen)?;
    std::panic::set_hook(Box::new(|info| {
        let _ = disable_raw_mode();
        let _ = execute!(std::io::stdout(), LeaveAlternateScreen);
        eprintln!("Panic: {}", info);
    }));

    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Event loop
    let mut tick = tokio::time::interval(Duration::from_millis(250));
    loop {
        tokio::select! {
            _ = tick.tick() => {
                terminal.draw(|f| app.draw(f))?;
            }
            Some(ev) = event_rx.recv() => {
                app.update(ev);
                terminal.draw(|f| app.draw(f))?;
                if app.should_quit { break; }
            }
        }
    }

    // Restore terminal
    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    // server is killed here when `server` is dropped
    drop(server);
    Ok(())
}
