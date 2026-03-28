# TUI Setup Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat-form SetupScreen with a three-step sequential wizard: provider select → API key input → model select.

**Architecture:** Single `SetupScreen` class maintains a `current_step: reactive[int]` (1/2/3). On each step change, `watch_current_step` clears and remounts widgets inside a `#step-content` container. No new files — only `setup.py` and its test file change.

**Tech Stack:** Python, Textual ≥0.50 (reactive, Select, Input, Vertical), pytest-asyncio

---

## File Map

| Action | Path |
|--------|------|
| Modify | `proteinclaw/cli/tui/screens/setup.py` |
| Modify | `tests/proteinclaw/tui/test_screens.py` (remove 3 old SetupScreen tests, add 7 new ones) |

---

### Task 1: Write failing tests for the wizard

**Files:**
- Modify: `tests/proteinclaw/tui/test_screens.py`

- [ ] **Step 1: Replace the three old SetupScreen tests with the new wizard tests**

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


# ── SetupScreen wizard helpers ─────────────────────────────────────────────────

class _SetupApp(App):
    """Minimal host that starts on SetupScreen."""

    async def on_mount(self) -> None:
        await self.push_screen(SetupScreen())


# ── Step 1: provider select ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wizard_step1_shows_provider_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        select = pilot.app.screen.query_one("#provider-select", Select)
        assert select is not None


# ── Step 1 → Step 2 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wizard_step1_anthropic_advances_to_api_key_input():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        inp = pilot.app.screen.query_one("#api-key-input", Input)
        assert inp is not None


@pytest.mark.asyncio
async def test_wizard_step2_label_contains_provider_display_name():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "deepseek"
        await pilot.pause()
        label_text = str(pilot.app.screen.query_one("#step-label", Label).renderable)
        assert "DeepSeek" in label_text


# ── Ollama skips step 2 ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wizard_ollama_skips_api_key_and_goes_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "ollama"
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


# ── Step 2 → Step 3 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wizard_enter_on_api_key_advances_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        pilot.app.screen.query_one("#api-key-input", Input).value = "sk-ant-test"
        await pilot.press("enter")
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


@pytest.mark.asyncio
async def test_wizard_escape_on_api_key_skips_and_advances_to_model_select():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        model_select = pilot.app.screen.query_one("#model-select", Select)
        assert model_select is not None


# ── Full flow: save_user_config called correctly ───────────────────────────────

@pytest.mark.asyncio
async def test_wizard_complete_saves_correct_key_and_model():
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
uv run pytest tests/proteinclaw/tui/test_screens.py -k "wizard" -v 2>&1 | head -60
```

Expected: All 7 `test_wizard_*` tests FAIL with `NoMatches` or similar (because `#provider-select` doesn't exist yet).

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/proteinclaw/tui/test_screens.py
git commit -m "test: replace flat-form setup tests with wizard step tests (failing)"
```

---

### Task 2: Rewrite SetupScreen as a three-step wizard

**Files:**
- Modify: `proteinclaw/cli/tui/screens/setup.py`

- [ ] **Step 1: Replace the entire file content**

```python
from __future__ import annotations

import proteinclaw.core.config as config_mod
from proteinclaw.core.config import SUPPORTED_MODELS

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Input, Label, Select


# (provider_id, display_name, env_key)  — env_key is "" for Ollama
_PROVIDERS: list[tuple[str, str, str]] = [
    ("anthropic", "Anthropic",                        "ANTHROPIC_API_KEY"),
    ("openai",    "OpenAI",                           "OPENAI_API_KEY"),
    ("deepseek",  "DeepSeek",                         "DEEPSEEK_API_KEY"),
    ("minimax",   "MiniMax",                          "MINIMAX_API_KEY"),
    ("ollama",    "Ollama (local, no API key needed)", ""),
]


def _models_for_provider(provider: str) -> list[str]:
    return [m for m, cfg in SUPPORTED_MODELS.items() if cfg["provider"] == provider]


class SetupScreen(Screen):
    """Three-step first-run wizard: provider → API key → model."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #setup-container {
        width: 64;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }
    #step-label {
        margin: 1 0 0 0;
        color: $text-muted;
    }
    #hint-label {
        color: $text-muted;
        margin: 0 0 1 0;
    }
    Input {
        margin: 0 0 1 0;
    }
    Select {
        margin: 0 0 1 0;
    }
    """

    current_step: reactive[int] = reactive(1)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_provider: str = ""
        self._api_key: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-container"):
            yield Label("Welcome to ProteinClaw!\n")
            yield Label("", id="step-label")
            yield Vertical(id="step-content")
            yield Label("", id="hint-label")

    async def on_mount(self) -> None:
        await self._render_step()

    async def watch_current_step(self, step: int) -> None:  # noqa: ARG002
        await self._render_step()

    async def _render_step(self) -> None:
        step = self.current_step
        content = self.query_one("#step-content", Vertical)
        step_label = self.query_one("#step-label", Label)
        hint_label = self.query_one("#hint-label", Label)

        await content.remove_children()

        if step == 1:
            step_label.update("Step 1 / 3 — Choose your LLM provider")
            hint_label.update("")
            options = [(display, pid) for pid, display, _ in _PROVIDERS]
            select: Select[str] = Select(options, id="provider-select")
            await content.mount(select)
            select.focus()

        elif step == 2:
            _, display_name, _ = next(p for p in _PROVIDERS if p[0] == self._selected_provider)
            step_label.update(f"Step 2 / 3 — {display_name} API Key")
            hint_label.update("Press Enter to continue, Escape to skip")
            inp = Input(placeholder="Paste your API key here", password=True, id="api-key-input")
            await content.mount(inp)
            inp.focus()

        elif step == 3:
            step_label.update("Step 3 / 3 — Default model")
            hint_label.update("Press Enter to confirm")
            models = _models_for_provider(self._selected_provider)
            options = [(m, m) for m in models]
            select = Select(options, id="model-select")
            await content.mount(select)
            select.focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            return

        if event.select.id == "provider-select":
            self._selected_provider = str(event.value)
            # Ollama needs no API key — jump straight to model selection
            self.current_step = 3 if self._selected_provider == "ollama" else 2

        elif event.select.id == "model-select":
            self._finish(str(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self._api_key = event.value.strip()
            self.current_step = 3

    def on_key(self, event) -> None:  # type: ignore[override]
        focused = self.focused
        if event.key == "escape" and getattr(focused, "id", None) == "api-key-input":
            self._api_key = ""
            self.current_step = 3

    def _finish(self, model: str) -> None:
        keys: dict[str, str] = {}
        if self._api_key and self._selected_provider != "ollama":
            _, _, env_key = next(p for p in _PROVIDERS if p[0] == self._selected_provider)
            if env_key:
                keys[env_key] = self._api_key

        config_mod.save_user_config(keys, model)
        config_mod.load_user_config()

        from proteinclaw.cli.tui.screens.main import MainScreen  # noqa: PLC0415
        self.app.switch_screen(MainScreen())
```

- [ ] **Step 2: Run the wizard tests to verify they pass**

```bash
cd /mnt/d/data/code/ProteinClaw
uv run pytest tests/proteinclaw/tui/test_screens.py -k "wizard" -v 2>&1 | tail -20
```

Expected: All 7 `test_wizard_*` tests PASS.

- [ ] **Step 3: Run the full test suite to confirm nothing else broke**

```bash
cd /mnt/d/data/code/ProteinClaw
uv run pytest tests/ -v 2>&1 | tail -30
```

Expected: All tests PASS. (The three old `test_setup_screen_*` tests were removed in Task 1.)

- [ ] **Step 4: Commit**

```bash
git add proteinclaw/cli/tui/screens/setup.py tests/proteinclaw/tui/test_screens.py
git commit -m "feat: replace flat setup form with three-step wizard (provider → key → model)"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Step 1 provider select (Anthropic/OpenAI/DeepSeek/MiniMax/Ollama) — Task 2
- [x] Step 2 API key input — Task 2
- [x] Step 3 model select filtered by provider — Task 2 (`_models_for_provider`)
- [x] Ollama skips Step 2 — Task 2 (`current_step = 3 if ollama`)
- [x] Model selector removed from wizard — no `Select` for models outside Step 3
- [x] `save_user_config` / `load_user_config` called unchanged — Task 2 `_finish()`
- [x] `switch_screen(MainScreen())` on completion — Task 2 `_finish()`

**Type consistency:**
- `_finish(model: str)` defined and called consistently
- `_models_for_provider(provider: str) -> list[str]` defined and used in Step 3
- `_PROVIDERS` list used in both `_render_step` and `_finish`
