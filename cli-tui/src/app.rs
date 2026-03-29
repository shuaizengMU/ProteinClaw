use crossterm::event::{KeyCode, KeyModifiers};
use ratatui::Frame;
use tokio::sync::mpsc::Sender;

use crate::config::{self, Config};
use crate::events::AppEvent;
use crate::views::{
    main_view::{self, MainAction, MainState},
    setup::{self, SetupState},
};

pub enum AppState {
    Setup(SetupState),
    Main(MainState),
}

pub struct App {
    pub state: AppState,
    pub should_quit: bool,
    ws_tx: Sender<String>,
}

impl App {
    pub fn new(cfg: Config, ws_tx: Sender<String>) -> Self {
        let state = if config::needs_setup(&cfg) {
            AppState::Setup(SetupState::new())
        } else {
            AppState::Main(MainState::new(cfg.default_model.clone(), ws_tx.clone()))
        };
        Self { state, should_quit: false, ws_tx }
    }

    /// Process one event, updating state in place.
    pub fn update(&mut self, event: AppEvent) {
        // Ctrl+C always quits globally
        if let AppEvent::Key(k) = &event {
            if k.code == KeyCode::Char('c') && k.modifiers.contains(KeyModifiers::CONTROL) {
                self.should_quit = true;
                return;
            }
        }

        match &mut self.state {
            AppState::Setup(setup_state) => {
                // Esc is NOT global quit here — setup uses it to skip the API key step
                if let AppEvent::Key(k) = event {
                    if let Some(result) = setup_state.handle_key(k) {
                        // Setup complete: transition to Main
                        self.state = AppState::Main(
                            MainState::new(result.config.default_model.clone(), self.ws_tx.clone())
                        );
                    }
                }
            }
            AppState::Main(main_state) => {
                // Esc quits only in Main state
                if let AppEvent::Key(k) = &event {
                    if k.code == KeyCode::Esc {
                        self.should_quit = true;
                        return;
                    }
                }
                match event {
                    AppEvent::Key(k) => {
                        if let Some(MainAction::Quit) = main_state.handle_key(k) {
                            self.should_quit = true;
                        }
                    }
                    AppEvent::WsMessage(agent_event) => {
                        main_state.handle_agent_event(agent_event);
                    }
                    AppEvent::WsError(msg) => {
                        main_state.handle_agent_event(crate::events::AgentEvent::Error(
                            format!("Connection error: {}", msg)
                        ));
                    }
                    AppEvent::Resize(_, _) | AppEvent::ServerReady(_) | AppEvent::ServerFailed(_) | AppEvent::Tick => {}
                }
            }
        }
    }

    /// Render the current state to the terminal frame.
    pub fn draw(&self, frame: &mut Frame) {
        match &self.state {
            AppState::Setup(s) => setup::draw(frame, s),
            AppState::Main(s)  => main_view::draw(frame, s),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use tokio::sync::mpsc;

    fn key(code: KeyCode) -> AppEvent {
        AppEvent::Key(KeyEvent::new(code, KeyModifiers::empty()))
    }

    fn make_app(needs_setup: bool) -> App {
        let (ws_tx, _) = mpsc::channel(8);
        let config = crate::config::Config {
            keys: if needs_setup {
                Default::default()
            } else {
                std::collections::HashMap::from([
                    ("OPENAI_API_KEY".into(), "sk-test".into())
                ])
            },
            default_model: "gpt-4o".into(),
        };
        App::new(config, ws_tx)
    }

    #[test]
    fn starts_in_setup_when_key_missing() {
        let app = make_app(true);
        assert!(matches!(app.state, AppState::Setup(_)));
    }

    #[test]
    fn starts_in_main_when_configured() {
        let app = make_app(false);
        assert!(matches!(app.state, AppState::Main(_)));
    }

    #[test]
    fn ctrl_c_sets_should_quit() {
        let mut app = make_app(false);
        use crossterm::event::KeyModifiers;
        let ev = AppEvent::Key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL));
        app.update(ev);
        assert!(app.should_quit);
    }

    #[test]
    fn esc_in_main_sets_should_quit() {
        let mut app = make_app(false);
        app.update(key(KeyCode::Esc));
        assert!(app.should_quit);
    }
}
