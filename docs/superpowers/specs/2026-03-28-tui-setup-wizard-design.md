# TUI Setup Screen Redesign — Codex Style

**Date:** 2026-03-28
**Status:** Approved

## Summary

Replace the current `SetupScreen` (flat form, then wizard with step counter) with a Codex-style progressive onboarding screen. Logic is unchanged: three sequential states (provider → API key → model). The change is purely visual: completed steps stack above the active card as plain-text summaries, the bordered card always contains only the current action.

## Motivation

The wizard's step counter ("Step 1/3") feels mechanical. Codex's approach is more natural: completed steps are acknowledged in-place and pushed upward; the user's attention stays on the single active card below. No explicit progress indicator is needed — context is visible from what has already been confirmed above.

## Setup Flow

### State 1 — Provider Selection
- Uses a Textual `Select`
- Action title: `Choose a provider`
- Helper text: `Provider decides which API key and models appear next.`
- Selecting a provider immediately advances (no Enter needed)
- Choosing Ollama skips API key state

### State 2 — API Key Entry
- Uses a password `Input`
- Action title: `Enter your <Provider> API key`
- Helper text: `Provider: <Provider>`
- `Enter` confirms and continues
- `Escape` or empty input skips

### State 3 — Model Selection
- Uses a Textual `Select`
- Action title: `Choose a default model`
- Helper text: `Provider: <Provider>`
- Selecting a model immediately completes setup

### Completion
- Calls `save_user_config(keys, default_model)`
- Calls `config_mod.load_user_config()`
- Transitions to `MainScreen` via `self.app.switch_screen(MainScreen())`

## Visual Layout

**State 1 (initial):**
```
               ProteinClaw
       Set up your default model to get started.


    +----------------------------------------------+
    | Choose a provider                            |
    |                                              |
    | [ Anthropic                            v ]   |
    |                                              |
    | Provider decides which API key and models    |
    | appear next.                                 |
    +----------------------------------------------+
```

**State 2 (after provider selected):**
```
               ProteinClaw
       Set up your default model to get started.

  ✓ Provider  Anthropic


    +----------------------------------------------+
    | Enter your Anthropic API key                 |
    |                                              |
    | [ ********************                   ]   |
    |                                              |
    | Provider: Anthropic                          |
    +----------------------------------------------+

    Enter continue   Esc skip
```

**State 3 (after API key):**
```
               ProteinClaw
       Set up your default model to get started.

  ✓ Provider  Anthropic
  ✓ API key   entered


    +----------------------------------------------+
    | Choose a default model                       |
    |                                              |
    | [ claude-opus-4-5                      v ]   |
    |                                              |
    | Provider: Anthropic                          |
    +----------------------------------------------+

    Select a model to continue
```

## Completed Step Summaries

| State completed | Summary text shown |
|---|---|
| Provider (non-Ollama) | `✓ Provider  <display_name>` |
| Provider (Ollama) | `✓ Provider  Ollama (local)` |
| API key entered | `✓ API key   entered` |
| API key skipped | `✓ API key   skipped` |

## Implementation Architecture

### Structural change from current wizard

Current: `watch_current_step` clears `#step-content` and remounts new widgets.

New: On step completion, **append** a `Static` summary above the card. The card's interior (`#card-content`) is still cleared and remounted for the new step. The card itself persists throughout.

### Layout tree

```
SetupScreen
└── Vertical (centered, full screen)
    ├── Label "#title"           — "ProteinClaw"
    ├── Label "#subtitle"        — "Set up your default model to get started."
    ├── Vertical "#summaries"    — completed step summaries (Static widgets appended here)
    ├── Vertical "#card"         — bordered card (border: solid $primary)
    │   ├── Label "#action-title"
    │   ├── Vertical "#card-content"  — Select or Input (remounted each step)
    │   └── Label "#helper-text"
    └── Label "#footer-hint"     — keyboard hints (updated each step)
```

### Internal state

```python
_selected_provider: str      # set after State 1
_api_key: str                # set after State 2, may be empty
current_step: reactive[int]  # 1, 2, or 3; drives card content
```

### Step advancement

- Provider selected → append provider summary → set `current_step = 2` (or 3 for Ollama)
- API key submitted (Enter) → append API key summary → set `current_step = 3`
- API key skipped (Escape/empty) → append "skipped" summary → set `current_step = 3`
- Model selected → call `_finish(model)`

### watch_current_step behaviour

Clears and remounts only `#card-content`. Updates `#action-title`, `#helper-text`, `#footer-hint`. Does NOT touch `#summaries`.

## Copy Rules

- Action titles are short imperative phrases, no step numbers
- Footer hint: empty on State 1, `Enter continue   Esc skip` on State 2, `Select a model to continue` on State 3
- Helper text inside card echoes current context

## Files Changed

- `proteinclaw/cli/tui/screens/setup.py` — rewrite
- `tests/proteinclaw/tui/test_screens.py` — update setup tests

## No Changes Required

- `proteinclaw/core/config.py`
- `proteinclaw/cli/tui/app.py`
- `proteinclaw/cli/tui/screens/main.py`

## Out of Scope

- Multi-provider configuration in one run
- Re-running setup from MainScreen
- Changes to `/model` in MainScreen
