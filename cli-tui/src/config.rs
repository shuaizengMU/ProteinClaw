use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct Config {
    pub model: String,
    pub server_port: u16,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            model: "gpt-4o".to_string(),
            server_port: 8765,
        }
    }
}

// ── TOML file schema ─────────────────────────────────────────────────────────

#[derive(Deserialize, Serialize, Default)]
struct TomlFile {
    #[serde(default)]
    keys: std::collections::HashMap<String, String>,
    #[serde(default)]
    defaults: TomlDefaults,
}

#[derive(Deserialize, Serialize, Default)]
struct TomlDefaults {
    model: Option<String>,
}

fn config_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home)
        .join(".config")
        .join("proteinclaw")
        .join("config.toml")
}

impl Config {
    pub fn load() -> Result<Self> {
        let path = config_path();
        let mut cfg = Config::default();

        if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            let toml: TomlFile = toml::from_str(&text)?;

            // Inject keys into env if not already set
            for (key, value) in &toml.keys {
                if !value.is_empty() && std::env::var(key).is_err() {
                    std::env::set_var(key, value);
                }
            }

            if let Some(model) = toml.defaults.model {
                if !model.is_empty() {
                    cfg.model = model;
                }
            }
        }

        Ok(cfg)
    }

    pub fn save(&self) -> Result<()> {
        let path = config_path();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        // Read existing file so we preserve keys
        let existing: TomlFile = if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            toml::from_str(&text).unwrap_or_default()
        } else {
            TomlFile::default()
        };

        let updated = TomlFile {
            keys: existing.keys,
            defaults: TomlDefaults {
                model: Some(self.model.clone()),
            },
        };

        std::fs::write(&path, toml::to_string(&updated)?)?;
        Ok(())
    }

    /// Save config and persist a single API key.
    pub fn save_with_key(&self, env_var: &str, key: &str) -> Result<()> {
        let path = config_path();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let mut existing: TomlFile = if path.exists() {
            let text = std::fs::read_to_string(&path)?;
            toml::from_str(&text).unwrap_or_default()
        } else {
            TomlFile::default()
        };

        existing.keys.insert(env_var.to_string(), key.to_string());
        existing.defaults.model = Some(self.model.clone());

        std::fs::write(&path, toml::to_string(&existing)?)?;
        Ok(())
    }

    /// Returns true if at least one provider API key is present in the environment.
    pub fn has_api_key() -> bool {
        let keys = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "MINIMAX_API_KEY",
            "GEMINI_API_KEY",
            "DASHSCOPE_API_KEY",
            "OPENROUTER_API_KEY",
        ];
        keys.iter()
            .any(|k| std::env::var(k).map(|v| !v.is_empty()).unwrap_or(false))
    }
}
