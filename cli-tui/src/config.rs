use std::collections::HashMap;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone)]
pub struct Config {
    pub keys: HashMap<String, String>,
    pub default_model: String,
}

/// Provider info used in SetupView.
pub struct Provider {
    pub id: &'static str,
    pub display: &'static str,
    pub env_key: &'static str,  // empty for Ollama
}

pub const PROVIDERS: &[Provider] = &[
    Provider { id: "anthropic", display: "Anthropic",                       env_key: "ANTHROPIC_API_KEY" },
    Provider { id: "openai",    display: "OpenAI",                          env_key: "OPENAI_API_KEY"    },
    Provider { id: "deepseek",  display: "DeepSeek",                        env_key: "DEEPSEEK_API_KEY"  },
    Provider { id: "minimax",   display: "MiniMax",                         env_key: "MINIMAX_API_KEY"   },
    Provider { id: "ollama",    display: "Ollama (local, no API key needed)", env_key: ""                },
];

pub fn models_for_provider(provider_id: &str) -> Vec<&'static str> {
    match provider_id {
        "anthropic" => vec!["claude-opus-4-5"],
        "openai"    => vec!["gpt-4o"],
        "deepseek"  => vec!["deepseek-chat", "deepseek-reasoner"],
        "minimax"   => vec!["minimax-text-01"],
        "ollama"    => vec!["ollama/llama3"],
        _           => vec![],
    }
}

/// Path to the shared config file.
pub fn config_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("~/.config"))
        .join("proteinclaw")
        .join("config.toml")
}

pub fn load() -> Config {
    load_from(config_path())
}

pub fn load_from(path: impl AsRef<Path>) -> Config {
    let Ok(text) = std::fs::read_to_string(path) else {
        return Config { keys: HashMap::new(), default_model: "gpt-4o".into() };
    };
    let Ok(doc) = text.parse::<toml::Table>() else {
        return Config { keys: HashMap::new(), default_model: "gpt-4o".into() };
    };
    let keys: HashMap<String, String> = doc.get("keys")
        .and_then(|v| v.as_table())
        .map(|t| t.iter()
            .filter_map(|(k, v)| v.as_str().map(|s| (k.clone(), s.to_string())))
            .filter(|(_, v)| !v.is_empty())
            .collect())
        .unwrap_or_default();
    let default_model = doc.get("defaults")
        .and_then(|v| v.as_table())
        .and_then(|t| t.get("model"))
        .and_then(|v| v.as_str())
        .unwrap_or("gpt-4o")
        .to_string();
    Config { keys, default_model }
}

pub fn save(config: &Config) -> anyhow::Result<()> {
    save_to(config, &config_path())
}

pub fn save_to(config: &Config, path: impl AsRef<Path>) -> anyhow::Result<()> {
    let path = path.as_ref();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut lines = vec!["[keys]\n".to_string()];
    for (k, v) in &config.keys {
        lines.push(format!("{} = \"{}\"\n", k, v));
    }
    lines.push("\n[defaults]\n".to_string());
    lines.push(format!("model = \"{}\"\n", config.default_model));
    std::fs::write(path, lines.join(""))?;
    Ok(())
}

/// Returns true if the API key for the current model's provider is absent.
/// Ollama never requires a key.
pub fn needs_setup(config: &Config) -> bool {
    let provider = provider_for_model(&config.default_model);
    if provider == "ollama" { return false; }
    let env_key = env_key_for_provider(provider);
    if env_key.is_empty() { return true; }
    !config.keys.contains_key(env_key)
}

fn provider_for_model(model: &str) -> &'static str {
    match model {
        "gpt-4o"              => "openai",
        "claude-opus-4-5"     => "anthropic",
        "deepseek-chat" | "deepseek-reasoner" => "deepseek",
        "minimax-text-01"     => "minimax",
        m if m.starts_with("ollama/") => "ollama",
        _                     => "",
    }
}

fn env_key_for_provider(provider: &str) -> &'static str {
    match provider {
        "openai"    => "OPENAI_API_KEY",
        "anthropic" => "ANTHROPIC_API_KEY",
        "deepseek"  => "DEEPSEEK_API_KEY",
        "minimax"   => "MINIMAX_API_KEY",
        _           => "",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use tempfile::TempDir;

    fn config_in(dir: &TempDir) -> std::path::PathBuf {
        dir.path().join("config.toml")
    }

    #[test]
    fn load_missing_file_returns_defaults() {
        let dir = TempDir::new().unwrap();
        let cfg = load_from(config_in(&dir));
        assert_eq!(cfg.default_model, "gpt-4o");
        assert!(cfg.keys.is_empty());
    }

    #[test]
    fn save_and_load_roundtrip() {
        let dir = TempDir::new().unwrap();
        let path = config_in(&dir);
        let cfg = Config {
            keys: HashMap::from([("DEEPSEEK_API_KEY".into(), "sk-abc".into())]),
            default_model: "deepseek-chat".into(),
        };
        save_to(&cfg, &path).unwrap();
        let loaded = load_from(path);
        assert_eq!(loaded.default_model, "deepseek-chat");
        assert_eq!(loaded.keys.get("DEEPSEEK_API_KEY").unwrap(), "sk-abc");
    }

    #[test]
    fn needs_setup_true_when_key_missing() {
        let cfg = Config {
            keys: HashMap::new(),
            default_model: "deepseek-chat".into(),
        };
        assert!(needs_setup(&cfg));
    }

    #[test]
    fn needs_setup_false_when_key_present() {
        let cfg = Config {
            keys: HashMap::from([("DEEPSEEK_API_KEY".into(), "sk-abc".into())]),
            default_model: "deepseek-chat".into(),
        };
        assert!(!needs_setup(&cfg));
    }

    #[test]
    fn needs_setup_false_for_ollama() {
        let cfg = Config {
            keys: HashMap::new(),
            default_model: "ollama/llama3".into(),
        };
        assert!(!needs_setup(&cfg));
    }
}
