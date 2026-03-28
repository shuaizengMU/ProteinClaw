# TUI Setup Wizard Redesign

**Date:** 2026-03-28
**Status:** Approved

## Summary

Replace the current flat-form `SetupScreen` (all fields shown at once) with a three-step sequential wizard inspired by OpenClaw's onboarding flow. One question per step, keyboard-driven navigation.

## Motivation

The current setup screen shows all four API key fields plus a model selector simultaneously. This is overwhelming and inconsistent with the project's single-focus TUI philosophy. The new wizard mirrors OpenClaw's approach: select provider → enter API key → select model.

## Wizard Flow

### Step 1 — Provider Selection (Select widget)
- Options: Anthropic, OpenAI, DeepSeek, MiniMax, Ollama
- Single-select using Textual `Select`
- **Selecting an option immediately advances** to Step 2 (no Enter needed)
- Ollama skips Step 2 (no API key required) and advances directly to Step 3

### Step 2 — API Key Entry (Input widget, password mode)
- Label shows which provider's key is needed
- `Enter` to confirm (empty value = skip)
- `Escape` to skip
- Skipped entirely when Ollama is selected

### Step 3 — Model Selection (Select widget)
- Options filtered from `SUPPORTED_MODELS` by chosen provider
- Single-select using Textual `Select`
- **Selecting an option immediately saves and transitions** to MainScreen (no Enter needed)

### Completion
- Calls `save_user_config(keys, default_model)` with the collected key and model
- Calls `config_mod.load_user_config()` to reinitialise the settings singleton
- Transitions to `MainScreen` via `self.app.switch_screen(MainScreen())`

## Provider → Key → Model Mapping

| Provider  | Env Key              | Models                              |
|-----------|----------------------|-------------------------------------|
| Anthropic | `ANTHROPIC_API_KEY`  | claude-opus-4-5                     |
| OpenAI    | `OPENAI_API_KEY`     | gpt-4o                              |
| DeepSeek  | `DEEPSEEK_API_KEY`   | deepseek-chat, deepseek-reasoner    |
| MiniMax   | `MINIMAX_API_KEY`    | minimax-text-01                     |
| Ollama    | _(none)_             | ollama/llama3                       |

## Visual Layout

```
╭─────────────────────────────────────────╮
│  Welcome to ProteinClaw                 │
│  Let's get you set up.                  │
╰─────────────────────────────────────────╯

  Step 1 / 3 — Choose your LLM provider
  ┌────────────────────────────────────────┐
  │ ❯ Anthropic                            │
  │   OpenAI                               │
  │   DeepSeek                             │
  │   MiniMax                              │
  │   Ollama (local, no API key needed)    │
  └────────────────────────────────────────┘
```

```
  Step 2 / 3 — Anthropic API Key
  ┌────────────────────────────────────────┐
  │ sk-ant-****                            │
  └────────────────────────────────────────┘
  Press Enter to continue, Escape to skip
```

```
  Step 3 / 3 — Default model
  ┌────────────────────────────────────────┐
  │ ❯ claude-opus-4-5                      │
  └────────────────────────────────────────┘
```

## Implementation

### Files changed
- `proteinclaw/cli/tui/screens/setup.py` — full rewrite
- `tests/proteinclaw/tui/test_screens.py` — remove 3 old flat-form tests, add 7 new wizard tests

### No changes required
- `proteinclaw/core/config.py` — `save_user_config`, `needs_setup`, `SUPPORTED_MODELS` unchanged
- `proteinclaw/cli/tui/app.py` — unchanged

### Internal state
```python
_selected_provider: str      # set after Step 1
_api_key: str                # set after Step 2 (may be empty)
current_step: reactive[int]  # 1, 2, or 3
```

### Step advancement logic
- Step 1 → Step 2: `Select.Changed` on `#provider-select` (skip to Step 3 if Ollama)
- Step 2 → Step 3: `Input.Submitted` (Enter) or `Escape` key on `#api-key-input`
- Step 3 → done: `Select.Changed` on `#model-select` → `_finish(model)` → save + switch_screen

### Widget rendering
`watch_current_step` clears and re-mounts step-specific widgets into a `#step-content` container. The `#step-label` and `#hint-label` update on each step.

## Out of Scope
- Multi-provider configuration (user configures one provider per wizard run)
- Re-running setup from the main screen (can be a future feature)
- Model selector removal from `/model` command (no change to MainScreen)
