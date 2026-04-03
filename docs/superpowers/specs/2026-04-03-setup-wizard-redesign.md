# Setup Wizard Redesign — Selectable Provider/Model/Key Flow

**Date:** 2026-04-03
**Goal:** Replace the current free-text model input in the TUI setup screen with a three-step guided wizard: select provider, select model, enter API key.

---

## Current State

The setup screen shows a static message ("No API key found") and a single text input for the model name. Users must know the exact model string and set API keys via environment variables before launching.

## New Flow

Three steps, each rendered as a centered popup with a selectable list or text input.

### Step 1: Select Provider

Vertical list, navigate with `Up/Down`, confirm with `Enter`.

```
┌─ ProteinClaw — Setup ─────────────┐
│                                    │
│  Select a provider:                │
│                                    │
│  > OpenAI                          │
│    Anthropic                       │
│    Google                          │
│    DeepSeek                        │
│    Qwen (DashScope)                │
│    MiniMax                         │
│    OpenRouter                      │
│    Ollama (local)                  │
│                                    │
│  [Up/Down] select  [Enter] confirm │
└────────────────────────────────────┘
```

### Step 2: Select Model

Filtered by chosen provider. Same navigation.

```
┌─ ProteinClaw — Setup ─────────────┐
│                                    │
│  Provider: DeepSeek                │
│  Select a model:                   │
│                                    │
│  > deepseek-chat                   │
│    deepseek-reasoner               │
│                                    │
│  [Up/Down] select  [Enter] confirm │
│  [Esc] back                        │
└────────────────────────────────────┘
```

### Step 3: Enter API Key

Text input with masked display. **Skipped entirely for Ollama** (no key needed — go straight to Chat).

```
┌─ ProteinClaw — Setup ─────────────┐
│                                    │
│  Provider: DeepSeek                │
│  Model:    deepseek-chat           │
│                                    │
│  Enter your DEEPSEEK_API_KEY:      │
│  sk-a1b2c3________________         │
│                                    │
│  [Enter] save  [Esc] back          │
└────────────────────────────────────┘
```

On `Enter`, the key is saved to `~/.config/proteinclaw/config.toml` under `[keys]`, the model is saved under `[defaults]`, and the screen transitions to `Screen::Chat`.

---

## Provider & Model Registry

| Provider | Display Name | Models | Env Var |
|----------|-------------|--------|---------|
| OpenAI | OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | Anthropic | `claude-opus-4-5` | `ANTHROPIC_API_KEY` |
| Google | Google | `gemini-2.5-pro`, `gemini-2.5-flash` | `GEMINI_API_KEY` |
| DeepSeek | DeepSeek | `deepseek-chat`, `deepseek-reasoner` | `DEEPSEEK_API_KEY` |
| Qwen | Qwen (DashScope) | `qwen-max`, `qwen-plus` | `DASHSCOPE_API_KEY` |
| MiniMax | MiniMax | `minimax-text-01` | `MINIMAX_API_KEY` |
| OpenRouter | OpenRouter | `openrouter/google/gemini-2.5-flash-preview-05-20` (free), `openrouter/deepseek/deepseek-chat-v3-0324` (free), `openrouter/meta-llama/llama-4-maverick` (free), `openrouter/qwen/qwen3-235b-a22b` (free), `openrouter/auto` | `OPENROUTER_API_KEY` |
| Ollama | Ollama (local) | `ollama/llama4`, `ollama/qwen3`, `ollama/llama3` | _(none)_ |

Free models in OpenRouter display with a `★free` suffix in the TUI list.

---

## Config Persistence

Saved to `~/.config/proteinclaw/config.toml`:

```toml
[keys]
DEEPSEEK_API_KEY = "sk-..."

[defaults]
model = "deepseek-chat"
```

On next launch, `Config::load()` reads this file, injects keys into env, and skips setup if a valid key exists for the configured model's provider.

---

## Code Changes

### `app.rs`

Replace `SetupField` and `SetupState` with:

```rust
pub enum SetupStep {
    Provider,
    Model,
    ApiKey,
}

pub struct SetupState {
    pub step: SetupStep,
    pub provider_idx: usize,
    pub model_idx: usize,
    pub key_buf: String,
    pub error: Option<String>,
}
```

New actions:
- `SetupUp` / `SetupDown` — move selection
- `SetupNext` — confirm current step (advance or save)
- `SetupBack` — go to previous step (or no-op on step 1)
- `SetupKeyInput(String)` — update key buffer

Add a static `PROVIDERS` registry (Vec of structs with name, models, env_var) in `app.rs` or a new `registry.rs`.

### `ui.rs`

Rewrite `draw_setup()` to render based on `st.step`:
- `Provider` — render provider list with highlight on `provider_idx`
- `Model` — render model list for selected provider with highlight on `model_idx`
- `ApiKey` — render provider/model summary + text input for key

### `main.rs`

Rewrite `handle_setup_key()`:
- `Up/Down` → `SetupUp/SetupDown`
- `Enter` → `SetupNext`
- `Esc` → `SetupBack`
- `Char(c)` / `Backspace` → only forwarded in `ApiKey` step

### `config.rs`

Update `save()` to accept and persist the API key alongside the model. Existing keys in the file are preserved.

### Python backend (`proteinclaw/core/config.py`)

Add new entries to `SUPPORTED_MODELS`:

```python
SUPPORTED_MODELS: dict[str, dict] = {
    "gpt-4o":            {"provider": "openai"},
    "claude-opus-4-5":   {"provider": "anthropic"},
    "gemini-2.5-pro":    {"provider": "google",    "api_base": "https://generativelanguage.googleapis.com/v1beta/openai"},
    "gemini-2.5-flash":  {"provider": "google",    "api_base": "https://generativelanguage.googleapis.com/v1beta/openai"},
    "deepseek-chat":     {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner": {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "qwen-max":          {"provider": "openai",    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "qwen-plus":         {"provider": "openai",    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "minimax-text-01":   {"provider": "openai",    "api_base": "https://api.minimax.chat/v1"},
    "openrouter/google/gemini-2.5-flash-preview-05-20": {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/deepseek/deepseek-chat-v3-0324":        {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/meta-llama/llama-4-maverick":            {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/qwen/qwen3-235b-a22b":                  {"provider": "openai", "api_base": "https://openrouter.ai/api/v1"},
    "openrouter/auto":   {"provider": "openai",    "api_base": "https://openrouter.ai/api/v1"},
    "ollama/llama4":     {"provider": "ollama",    "api_base": "http://localhost:11434"},
    "ollama/qwen3":      {"provider": "ollama",    "api_base": "http://localhost:11434"},
    "ollama/llama3":     {"provider": "ollama",    "api_base": "http://localhost:11434"},
}
```

Add `_PROVIDER_KEY_MAP` entries:
```python
"google":     "GEMINI_API_KEY",
"dashscope":  "DASHSCOPE_API_KEY",
"openrouter": "OPENROUTER_API_KEY",
```

Note: OpenRouter and Qwen (DashScope) use OpenAI-compatible APIs via `litellm`, so `provider: "openai"` with a custom `api_base` is correct. The env var for auth is mapped separately.
