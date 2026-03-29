use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    Frame,
    layout::{Alignment, Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph},
};

use crate::config::{self, Config, PROVIDERS, models_for_provider};

#[derive(Debug, Clone, PartialEq)]
pub enum SetupStep {
    ChooseProvider,
    EnterApiKey,
    ChooseModel,
}

pub struct SetupState {
    pub step: SetupStep,
    pub selected_provider: usize,
    pub api_key_input: String,
    pub selected_model: usize,
    models: Vec<&'static str>,
}

pub struct SetupResult {
    pub config: Config,
}

impl SetupState {
    pub fn new() -> Self {
        Self {
            step: SetupStep::ChooseProvider,
            selected_provider: 0,
            api_key_input: String::new(),
            selected_model: 0,
            models: vec![],
        }
    }

    /// Handle a key press. Returns `Some(SetupResult)` when setup is complete.
    pub fn handle_key(&mut self, key: KeyEvent) -> Option<SetupResult> {
        match self.step {
            SetupStep::ChooseProvider => self.handle_key_provider(key),
            SetupStep::EnterApiKey   => self.handle_key_api_key(key),
            SetupStep::ChooseModel   => self.handle_key_model(key),
        }
    }

    fn handle_key_provider(&mut self, key: KeyEvent) -> Option<SetupResult> {
        match key.code {
            KeyCode::Down => {
                if self.selected_provider + 1 < PROVIDERS.len() {
                    self.selected_provider += 1;
                }
            }
            KeyCode::Up => {
                self.selected_provider = self.selected_provider.saturating_sub(1);
            }
            KeyCode::Enter => {
                let provider = &PROVIDERS[self.selected_provider];
                if provider.id == "ollama" {
                    self.load_models();
                    self.step = SetupStep::ChooseModel;
                } else {
                    self.step = SetupStep::EnterApiKey;
                }
            }
            _ => {}
        }
        None
    }

    fn handle_key_api_key(&mut self, key: KeyEvent) -> Option<SetupResult> {
        match key.code {
            KeyCode::Char(c) => { self.api_key_input.push(c); }
            KeyCode::Backspace => { self.api_key_input.pop(); }
            KeyCode::Enter => {
                self.load_models();
                self.step = SetupStep::ChooseModel;
            }
            KeyCode::Esc => {
                self.api_key_input.clear();
                self.load_models();
                self.step = SetupStep::ChooseModel;
            }
            _ => {}
        }
        None
    }

    fn handle_key_model(&mut self, key: KeyEvent) -> Option<SetupResult> {
        match key.code {
            KeyCode::Down => {
                if self.selected_model + 1 < self.models.len() {
                    self.selected_model += 1;
                }
            }
            KeyCode::Up => {
                self.selected_model = self.selected_model.saturating_sub(1);
            }
            KeyCode::Enter => {
                if self.models.is_empty() { return None; }
                return Some(self.finish());
            }
            _ => {}
        }
        None
    }

    fn load_models(&mut self) {
        let pid = PROVIDERS[self.selected_provider].id;
        self.models = models_for_provider(pid);
        self.selected_model = 0;
    }

    fn finish(&self) -> SetupResult {
        let model = self.models[self.selected_model].to_string();
        let provider = &PROVIDERS[self.selected_provider];
        let mut keys = std::collections::HashMap::new();
        if !self.api_key_input.is_empty() && !provider.env_key.is_empty() {
            keys.insert(provider.env_key.to_string(), self.api_key_input.clone());
        }
        let cfg = Config { keys, default_model: model };
        let _ = config::save(&cfg);
        SetupResult { config: cfg }
    }
}

pub fn draw(frame: &mut Frame, state: &SetupState) {
    let area = frame.area();

    // Center a 66-wide, 20-tall card
    let card_w = 66u16.min(area.width);
    let card_h = 20u16.min(area.height);
    let x = area.width.saturating_sub(card_w) / 2;
    let y = area.height.saturating_sub(card_h) / 2;
    let outer = Rect::new(x, y, card_w, card_h);

    let chunks = Layout::vertical([
        Constraint::Length(1), // title
        Constraint::Length(1), // subtitle
        Constraint::Length(1), // spacer
        Constraint::Min(0),    // card
        Constraint::Length(1), // footer hint
    ])
    .split(outer);

    frame.render_widget(
        Paragraph::new("ProteinClaw")
            .alignment(Alignment::Center)
            .style(Style::default().add_modifier(Modifier::BOLD)),
        chunks[0],
    );
    frame.render_widget(
        Paragraph::new("Set up your default model to get started.")
            .alignment(Alignment::Center)
            .style(Style::default().fg(Color::DarkGray)),
        chunks[1],
    );

    let card_block = Block::default().borders(Borders::ALL);
    let card_inner = card_block.inner(chunks[3]);
    frame.render_widget(card_block, chunks[3]);

    match state.step {
        SetupStep::ChooseProvider => draw_provider_step(frame, state, card_inner),
        SetupStep::EnterApiKey    => draw_api_key_step(frame, state, card_inner),
        SetupStep::ChooseModel    => draw_model_step(frame, state, card_inner),
    }

    let hint = match state.step {
        SetupStep::ChooseProvider => "↑↓ navigate   Enter select",
        SetupStep::EnterApiKey    => "Enter continue   Esc skip",
        SetupStep::ChooseModel    => "↑↓ navigate   Enter select",
    };
    frame.render_widget(
        Paragraph::new(hint).style(Style::default().fg(Color::DarkGray)),
        chunks[4],
    );
}

fn draw_provider_step(frame: &mut Frame, state: &SetupState, area: Rect) {
    let chunks = Layout::vertical([
        Constraint::Length(1), // action title
        Constraint::Length(1), // helper
        Constraint::Min(0),    // list
    ])
    .split(area);

    frame.render_widget(
        Paragraph::new("Choose a provider").style(Style::default().add_modifier(Modifier::BOLD)),
        chunks[0],
    );
    frame.render_widget(
        Paragraph::new("Provider decides which API key and models appear next.")
            .style(Style::default().fg(Color::DarkGray)),
        chunks[1],
    );

    let items: Vec<ListItem> = PROVIDERS.iter().enumerate()
        .map(|(i, p)| {
            let prefix = if i == state.selected_provider { "▶ " } else { "  " };
            ListItem::new(format!("{}{}", prefix, p.display))
        })
        .collect();
    let mut list_state = ListState::default().with_selected(Some(state.selected_provider));
    frame.render_stateful_widget(List::new(items), chunks[2], &mut list_state);
}

fn draw_api_key_step(frame: &mut Frame, state: &SetupState, area: Rect) {
    let provider = &PROVIDERS[state.selected_provider];
    let chunks = Layout::vertical([
        Constraint::Length(1),
        Constraint::Length(1),
        Constraint::Length(1),
    ])
    .split(area);

    frame.render_widget(
        Paragraph::new(format!("Enter your {} API key", provider.display))
            .style(Style::default().add_modifier(Modifier::BOLD)),
        chunks[0],
    );
    let masked: String = "•".repeat(state.api_key_input.len());
    let display = if masked.is_empty() { "Paste your API key here".to_string() } else { masked };
    let style = if state.api_key_input.is_empty() {
        Style::default().fg(Color::DarkGray)
    } else {
        Style::default()
    };
    frame.render_widget(Paragraph::new(display).style(style), chunks[1]);
    frame.render_widget(
        Paragraph::new("Stored locally and only used for this provider.")
            .style(Style::default().fg(Color::DarkGray)),
        chunks[2],
    );
}

fn draw_model_step(frame: &mut Frame, state: &SetupState, area: Rect) {
    let provider = &PROVIDERS[state.selected_provider];
    let chunks = Layout::vertical([
        Constraint::Length(1),
        Constraint::Length(1),
        Constraint::Min(0),
    ])
    .split(area);

    frame.render_widget(
        Paragraph::new("Choose a default model").style(Style::default().add_modifier(Modifier::BOLD)),
        chunks[0],
    );
    frame.render_widget(
        Paragraph::new(format!("Provider: {}", provider.display))
            .style(Style::default().fg(Color::DarkGray)),
        chunks[1],
    );

    let items: Vec<ListItem> = state.models.iter().enumerate()
        .map(|(i, m)| {
            let prefix = if i == state.selected_model { "▶ " } else { "  " };
            ListItem::new(format!("{}{}", prefix, m))
        })
        .collect();
    let mut list_state = ListState::default().with_selected(Some(state.selected_model));
    frame.render_stateful_widget(List::new(items), chunks[2], &mut list_state);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

    fn key(code: KeyCode) -> KeyEvent {
        KeyEvent::new(code, KeyModifiers::empty())
    }

    #[test]
    fn starts_at_choose_provider() {
        let state = SetupState::new();
        assert!(matches!(state.step, SetupStep::ChooseProvider));
        assert_eq!(state.selected_provider, 0);
    }

    #[test]
    fn arrow_down_moves_cursor() {
        let mut state = SetupState::new();
        state.handle_key(key(KeyCode::Down));
        assert_eq!(state.selected_provider, 1);
    }

    #[test]
    fn arrow_up_wraps() {
        let mut state = SetupState::new();
        state.handle_key(key(KeyCode::Up));
        assert_eq!(state.selected_provider, 0);
    }

    #[test]
    fn enter_on_non_ollama_advances_to_api_key() {
        let mut state = SetupState::new();
        let result = state.handle_key(key(KeyCode::Enter));
        assert!(result.is_none());
        assert!(matches!(state.step, SetupStep::EnterApiKey));
    }

    #[test]
    fn enter_on_ollama_skips_to_choose_model() {
        let mut state = SetupState::new();
        for _ in 0..4 {
            state.handle_key(key(KeyCode::Down));
        }
        state.handle_key(key(KeyCode::Enter));
        assert!(matches!(state.step, SetupStep::ChooseModel));
        assert!(state.api_key_input.is_empty());
    }

    #[test]
    fn typing_appends_to_api_key() {
        let mut state = SetupState::new();
        state.handle_key(key(KeyCode::Enter)); // enter step 2
        state.handle_key(key(KeyCode::Char('a')));
        state.handle_key(key(KeyCode::Char('b')));
        assert_eq!(state.api_key_input, "ab");
    }

    #[test]
    fn esc_on_api_key_step_skips_with_empty_key() {
        let mut state = SetupState::new();
        state.handle_key(key(KeyCode::Enter)); // enter step 2
        state.handle_key(key(KeyCode::Char('x')));
        state.handle_key(key(KeyCode::Esc));
        assert!(state.api_key_input.is_empty());
        assert!(matches!(state.step, SetupStep::ChooseModel));
    }

    #[test]
    fn enter_on_model_returns_setup_result() {
        let mut state = SetupState::new();
        state.handle_key(key(KeyCode::Enter)); // → EnterApiKey
        state.handle_key(key(KeyCode::Enter)); // → ChooseModel (empty key)
        let result = state.handle_key(key(KeyCode::Enter)); // select first model
        assert!(result.is_some());
    }
}
