# TUI Setup Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat-form `SetupScreen` with a Codex-style single-screen setup flow that preserves the existing sequence: provider select -> API key input -> model select.

**Architecture:** A single `SetupScreen` class keeps `current_step: reactive[int]` (1/2/3). The outer layout stays mounted as one centered onboarding card, while `watch_current_step` clears and remounts widgets inside a `#step-content` container. No new production files; only `setup.py` and its test file change.

**Tech Stack:** Python, Textual >=0.50 (reactive, Select, Input, Vertical), pytest-asyncio

---

## File Map

| Action | Path |
|--------|------|
| Modify | `proteinclaw/cli/tui/screens/setup.py` |
| Modify | `tests/proteinclaw/tui/test_screens.py` (remove old flat-form tests, add setup-flow tests) |

---

### Task 1: Write failing tests for the single-screen setup flow

**Files:**
- Modify: `tests/proteinclaw/tui/test_screens.py`

- [ ] **Step 1: Replace the old SetupScreen tests with setup-flow tests**

Open `tests/proteinclaw/tui/test_screens.py`. Remove everything between the top imports and `class _MainApp` that references `_SetupApp` or `SetupScreen`, then add the following block in its place:

```python
from __future__ import annotations
import os
from unittest.mock import patch

import pytest
import proteinclaw.core.config as config_mod
from proteinclaw.cli.tui.screens.setup import SetupScreen
from textual.app import App, ComposeResult
from textual.widgets import Input, Label, Select


# SetupScreen setup-flow helpers

class _SetupApp(App):
    """Minimal host that starts on SetupScreen."""

    async def on_mount(self) -> None:
        await self.push_screen(SetupScreen())


@pytest.mark.asyncio
async def test_setup_flow_initial_state_shows_provider_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        select = pilot.app.screen.query_one("#provider-select", Select)
        assert select is not None


@pytest.mark.asyncio
async def test_setup_flow_provider_selection_advances_to_api_key_input():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        inp = pilot.app.screen.query_one("#api-key-input", Input)
        assert inp is not None


@pytest.mark.asyncio
async def test_setup_flow_api_key_label_contains_provider_display_name():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "deepseek"
        await pilot.pause()
        label_text = str(pilot.app.screen.query_one("#step-label", Label).renderable)
        assert "DeepSeek" in label_text


@pytest.mark.asyncio
async def test_setup_flow_ollama_skips_api_key_and_goes_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "ollama"
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


@pytest.mark.asyncio
async def test_setup_flow_enter_on_api_key_advances_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        pilot.app.screen.query_one("#api-key-input", Input).value = "sk-ant-test"
        await pilot.press("enter")
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


@pytest.mark.asyncio
async def test_setup_flow_escape_on_api_key_skips_and_advances_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


@pytest.mark.asyncio
async def test_setup_flow_complete_saves_correct_key_and_model():
    saved: list[tuple] = []

    def _fake_save(keys, model):
        saved.append((keys, model))

    with patch.object(config_mod, "save_user_config", _fake_save), \
         patch.object(config_mod, "load_user_config", lambda: None), \
         patch("proteinclaw.cli.tui.screens.setup.MainScreen"):
        async with _SetupApp().run_test(size=(120, 50)) as pilot:
            pilot.app.screen.query_one("#provider-select", Select).value = "deepseek"
            await pilot.pause()
            pilot.app.screen.query_one("#api-key-input", Input).value = "ds-key"
            await pilot.press("enter")
            await pilot.pause()
            pilot.app.screen.query_one("#model-select", Select).value = "deepseek-chat"
            await pilot.pause()

    assert len(saved) == 1
    assert saved[0][0] == {"DEEPSEEK_API_KEY": "ds-key"}
    assert saved[0][1] == "deepseek-chat"
```

- [ ] **Step 2: Run the new tests to confirm they all fail (SetupScreen not yet changed)**

```bash
cd /mnt/d/data/code/ProteinClaw
uv run pytest tests/proteinclaw/tui/test_screens.py -k "setup_flow" -v 2>&1 | head -60
```

Expected: All 7 `test_setup_flow_*` tests FAIL with `NoMatches` or similar, because the progressive single-screen UI does not exist yet.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/proteinclaw/tui/test_screens.py
git commit -m "test: replace flat-form setup tests with setup-flow tests (failing)"
```

---

### Task 2: Rewrite SetupScreen as a Codex-style single-screen flow

**Files:**
- Modify: `proteinclaw/cli/tui/screens/setup.py`

- [ ] **Step 1: Replace the setup screen implementation**

Implementation requirements:

- Keep a single `SetupScreen`
- Preserve the existing provider -> API key -> model logic
- Keep `current_step` as the state driver
- Keep `#step-content` as the container for the active control
- Update labels and CSS so the screen feels like a centered onboarding card, not a wizard

Expected structural changes:

```python
class SetupScreen(Screen):
    """Single-screen first-run setup flow: provider -> API key -> model."""
```

```python
def compose(self) -> ComposeResult:
    with Vertical(id="setup-container"):
        yield Label("ProteinClaw", id="title")
        yield Label("Set up your default model to get started.", id="subtitle")
        yield Label("", id="step-label")
        yield Vertical(id="step-content")
        yield Label("", id="context-label")
        yield Label("", id="hint-label")
```

State copy expectations:

- Provider state title: `Choose a provider`
- Provider state hint: `Provider decides which API key and models appear next.`
- API key state title: `Enter your <Provider> API key`
- API key state hint: `Enter continue   Esc skip`
- Model state title: `Choose a default model`
- Model state hint: `Select a model to finish`

Behavior requirements:

- Selecting a provider immediately advances
- Ollama skips API key state
- Enter on API key advances
- Escape on API key skips
- Selecting a model immediately saves and transitions to `MainScreen`

- [ ] **Step 2: Run the setup-flow tests to verify they pass**

```bash
cd /mnt/d/data/code/ProteinClaw
uv run pytest tests/proteinclaw/tui/test_screens.py -k "setup_flow" -v 2>&1 | tail -20
```

Expected: All 7 `test_setup_flow_*` tests PASS.

- [ ] **Step 3: Run the full test suite to confirm nothing else broke**

```bash
cd /mnt/d/data/code/ProteinClaw
uv run pytest tests/ -v 2>&1 | tail -30
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add proteinclaw/cli/tui/screens/setup.py tests/proteinclaw/tui/test_screens.py
git commit -m "feat: redesign setup screen as codex-style setup flow"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Initial provider selection state (Anthropic/OpenAI/DeepSeek/MiniMax/Ollama) - Task 2
- [x] API key state with provider-aware label - Task 2
- [x] Model selection state filtered by provider - Task 2 (`_models_for_provider`)
- [x] Ollama skips API key state - Task 2 (`current_step = 3 if ollama`)
- [x] Single-screen codex-style centered card layout - Task 2 CSS and labels
- [x] `save_user_config` / `load_user_config` called unchanged - Task 2 `_finish()`
- [x] `switch_screen(MainScreen())` on completion - Task 2 `_finish()`

**Type consistency:**
- `_finish(model: str)` defined and called consistently
- `_models_for_provider(provider: str) -> list[str]` defined and used in model state
- `_PROVIDERS` list used in both `_render_step` and `_finish`
