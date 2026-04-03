pub struct ModelEntry {
    pub name: &'static str,
    /// Display suffix shown in the TUI list (e.g. "★free")
    pub tag: &'static str,
}

pub struct Provider {
    pub name: &'static str,
    pub models: &'static [ModelEntry],
    /// Environment variable name for the API key. Empty string means no key needed.
    pub env_var: &'static str,
}

pub static PROVIDERS: &[Provider] = &[
    Provider {
        name: "OpenAI",
        models: &[ModelEntry { name: "gpt-4o", tag: "" }],
        env_var: "OPENAI_API_KEY",
    },
    Provider {
        name: "Anthropic",
        models: &[ModelEntry { name: "claude-opus-4-5", tag: "" }],
        env_var: "ANTHROPIC_API_KEY",
    },
    Provider {
        name: "Google",
        models: &[
            ModelEntry { name: "gemini-2.5-pro", tag: "" },
            ModelEntry { name: "gemini-2.5-flash", tag: "" },
        ],
        env_var: "GEMINI_API_KEY",
    },
    Provider {
        name: "DeepSeek",
        models: &[
            ModelEntry { name: "deepseek-chat", tag: "" },
            ModelEntry { name: "deepseek-reasoner", tag: "" },
        ],
        env_var: "DEEPSEEK_API_KEY",
    },
    Provider {
        name: "Qwen (DashScope)",
        models: &[
            ModelEntry { name: "qwen-max", tag: "" },
            ModelEntry { name: "qwen-plus", tag: "" },
        ],
        env_var: "DASHSCOPE_API_KEY",
    },
    Provider {
        name: "MiniMax",
        models: &[ModelEntry { name: "minimax-text-01", tag: "" }],
        env_var: "MINIMAX_API_KEY",
    },
    Provider {
        name: "OpenRouter",
        models: &[
            ModelEntry { name: "openrouter/google/gemini-2.5-flash-preview-05-20", tag: "★free" },
            ModelEntry { name: "openrouter/deepseek/deepseek-chat-v3-0324", tag: "★free" },
            ModelEntry { name: "openrouter/meta-llama/llama-4-maverick", tag: "★free" },
            ModelEntry { name: "openrouter/qwen/qwen3-235b-a22b", tag: "★free" },
            ModelEntry { name: "openrouter/auto", tag: "" },
        ],
        env_var: "OPENROUTER_API_KEY",
    },
    Provider {
        name: "Ollama (local)",
        models: &[
            ModelEntry { name: "ollama/llama4", tag: "" },
            ModelEntry { name: "ollama/qwen3", tag: "" },
            ModelEntry { name: "ollama/llama3", tag: "" },
        ],
        env_var: "",
    },
];
