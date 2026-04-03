use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_model")]
    pub model: String,
    #[serde(default = "default_port")]
    pub server_port: u16,
}

fn default_model() -> String {
    "claude-3-5-sonnet-20241022".to_string()
}
fn default_port() -> u16 {
    8000
}

impl Default for Config {
    fn default() -> Self {
        Self {
            model: default_model(),
            server_port: default_port(),
        }
    }
}

impl Config {
    pub fn config_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("proteinclaw")
            .join("config.toml")
    }

    pub fn load() -> Result<Self> {
        let path = Self::config_path();
        let text = std::fs::read_to_string(path)?;
        Ok(toml::from_str(&text)?)
    }

    pub fn save(&self) -> Result<()> {
        let path = Self::config_path();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(path, toml::to_string_pretty(self)?)?;
        Ok(())
    }

    /// Returns true if at least one API key env var is set.
    pub fn has_api_key() -> bool {
        std::env::var("ANTHROPIC_API_KEY").is_ok()
            || std::env::var("OPENAI_API_KEY").is_ok()
            || std::env::var("DEEPSEEK_API_KEY").is_ok()
            || std::env::var("MINIMAX_API_KEY").is_ok()
    }
}
