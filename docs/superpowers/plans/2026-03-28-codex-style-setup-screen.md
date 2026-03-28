# Codex-Style Setup Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the step-counter wizard UI with a Codex B2-style progressive onboarding screen where completed steps stack as plain-text summaries above the active bordered card.

**Architecture:** The three-step logic (provider → API key → model) and all config calls are unchanged. Only the visual structure changes: `compose()` gains a persistent outer layout (title, subtitle, `#summaries`, `#card`, `#footer-hint`); `_render_step()` swaps only `#card-content`; step-completion handlers append `Label` summaries to `#summaries` before advancing `current_step`.

**Tech Stack:** Python, Textual ≥0.50 (Label, Select, Input, Vertical, reactive), pytest-asyncio

---

## File Map

| Action | Path |
|--------|------|
| Modify | `proteinclaw/cli/tui/screens/setup.py` |
| Modify | `tests/proteinclaw/tui/test_screens.py` |

---

### Task 1: Update tests to match new layout (TDD — write failing tests first)

**Files:**
- Modify: `tests/proteinclaw/tui/test_screens.py`

- [ ] **Step 1: Update the label-text test to query `#action-title` instead of `#step-label`**

In `tests/proteinclaw/tui/test_screens.py`, find `test_setup_flow_api_key_label_contains_provider_display_name` (currently queries `#step-label`). Replace the whole function with:

```python
@pytest.mark.asyncio
async def test_setup_flow_api_key_label_contains_provider_display_name():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "deepseek"
        await pilot.pause()
        label_text = str(pilot.app.screen.query_one("#action-title", Label).renderable)
        assert "DeepSeek" in label_text
```

- [ ] **Step 2: Add two new tests for summary visibility — append them before the `_MainApp` import block**

```python
@pytest.mark.asyncio
async def test_setup_flow_provider_summary_visible_after_selection():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        labels = pilot.app.screen.query_one("#summaries", Vertical).query(Label)
        texts = [str(lbl.renderable) for lbl in labels]
        assert any("Anthropic" in t for t in texts)


@pytest.mark.asyncio
async def test_setup_flow_api_key_summary_visible_after_submission():
    async with _SetupApp().run_test(size=(120, 50)) as pilot:
        pilot.app.screen.query_one("#provider-select", Select).value = "anthropic"
        await pilot.pause()
        pilot.app.screen.query_one("#api-key-input", Input).value = "sk-test"
        await pilot.press("enter")
        await pilot.pause()
        labels = pilot.app.screen.query_one("#summaries", Vertical).query(Label)
        texts = [str(lbl.renderable) for lbl in labels]
        assert any("entered" in t for t in texts)
```

Also add `Vertical` to the imports at the top of the test file (it's needed for `query_one("#summaries", Vertical)`):

```python
from textual.containers import Vertical
```

- [ ] **Step 3: Run the updated and new tests — expect failures**

```bash
cd /home/zengs/data/code/ProteinClaw
pytest tests/proteinclaw/tui/test_screens.py -k "setup_flow" -v 2>&1 | tail -20
```

Expected: `test_setup_flow_api_key_label_contains_provider_display_name` FAILS (`NoMatches` for `#action-title`), two new tests FAIL (`NoMatches` for `#summaries`). The other 5 setup flow tests may still pass or fail — that's fine.

- [ ] **Step 4: Confirm the `_MainApp` tests still pass**

```bash
pytest tests/proteinclaw/tui/test_screens.py -k "main_screen" -v 2>&1 | tail -10
```

Expected: all 5 `_MainApp` tests PASS (we didn't touch them).

- [ ] **Step 5: Commit the failing tests**

```bash
git add tests/proteinclaw/tui/test_screens.py
git commit -m "test: update setup tests for Codex B2 layout (failing — pre-implementation)"
```

---

### Task 2: Rewrite SetupScreen to Codex B2 layout

**Files:**
- Modify: `proteinclaw/cli/tui/screens/setup.py`

- [ ] **Step 1: Replace the entire file with the Codex B2 implementation**

```python
from __future__ import annotations

import proteinclaw.core.config as config_mod
from proteinclaw.core.config import SUPPORTED_MODELS
from proteinclaw.cli.tui.screens.main import MainScreen

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

# Providers that reuse another provider's SDK in SUPPORTED_MODELS but are distinct in the wizard
_PROVIDER_MODELS_OVERRIDE: dict[str, list[str]] = {
    "minimax": ["minimax-text-01"],
}


def _models_for_provider(provider: str) -> list[str]:
    if provider in _PROVIDER_MODELS_OVERRIDE:
        return _PROVIDER_MODELS_OVERRIDE[provider]
    return [m for m, cfg in SUPPORTED_MODELS.items() if cfg["provider"] == provider]


def _display_name(provider_id: str) -> str:
    return next(display for pid, display, _ in _PROVIDERS if pid == provider_id)


class SetupScreen(Screen):
    """Codex-style progressive onboarding: completed steps stack above the active card."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #outer {
        width: 64;
        height: auto;
    }
    #title {
        text-align: center;
        text-style: bold;
        margin: 0 0 0 0;
    }
    #subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }
    #summaries {
        margin: 0 0 1 2;
        height: auto;
    }
    #card {
        border: solid $primary;
        padding: 1 2;
        height: auto;
    }
    #action-title {
        text-style: bold;
        margin: 0 0 1 0;
    }
    #helper-text {
        color: $text-muted;
        margin: 1 0 0 0;
    }
    #footer-hint {
        color: $text-muted;
        margin: 1 0 0 2;
    }
    Input {
        margin: 0 0 0 0;
    }
    Select {
        margin: 0 0 0 0;
    }
    """

    current_step: reactive[int] = reactive(1, init=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_provider: str = ""
        self._api_key: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="outer"):
            yield Label("ProteinClaw", id="title")
            yield Label("Set up your default model to get started.", id="subtitle")
            yield Vertical(id="summaries")
            with Vertical(id="card"):
                yield Label("", id="action-title")
                yield Vertical(id="card-content")
                yield Label("", id="helper-text")
            yield Label("", id="footer-hint")

    async def on_mount(self) -> None:
        await self._render_step()

    async def watch_current_step(self, step: int) -> None:  # noqa: ARG002
        await self._render_step()

    async def _render_step(self) -> None:
        step = self.current_step
        card_content = self.query_one("#card-content", Vertical)
        action_title = self.query_one("#action-title", Label)
        helper_text = self.query_one("#helper-text", Label)
        footer_hint = self.query_one("#footer-hint", Label)

        await card_content.remove_children()

        if step == 1:
            action_title.update("Choose a provider")
            helper_text.update("Provider decides which API key and models appear next.")
            footer_hint.update("")
            options = [(display, pid) for pid, display, _ in _PROVIDERS]
            select: Select[str] = Select(options, id="provider-select")
            await card_content.mount(select)
            select.focus()

        elif step == 2:
            name = _display_name(self._selected_provider)
            action_title.update(f"Enter your {name} API key")
            helper_text.update(f"Provider: {name}")
            footer_hint.update("Enter continue   Esc skip")
            inp = Input(placeholder="Paste your API key here", password=True, id="api-key-input")
            await card_content.mount(inp)
            inp.focus()

        elif step == 3:
            name = _display_name(self._selected_provider)
            action_title.update("Choose a default model")
            helper_text.update(f"Provider: {name}")
            footer_hint.update("Select a model to continue")
            models = _models_for_provider(self._selected_provider)
            options = [(m, m) for m in models]
            select = Select(options, id="model-select")
            await card_content.mount(select)
            select.focus()

    async def _append_summary(self, text: str) -> None:
        summaries = self.query_one("#summaries", Vertical)
        await summaries.mount(Label(text))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            return

        if event.select.id == "provider-select":
            self._selected_provider = str(event.value)
            name = _display_name(self._selected_provider)
            if self._selected_provider == "ollama":
                self.call_after_refresh(self._advance_with_summary,
                                        f"✓ Provider  {name}", 3)
            else:
                self.call_after_refresh(self._advance_with_summary,
                                        f"✓ Provider  {name}", 2)

        elif event.select.id == "model-select":
            self._finish(str(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self._api_key = event.value.strip()
            summary = "✓ API key   entered" if self._api_key else "✓ API key   skipped"
            self.call_after_refresh(self._advance_with_summary, summary, 3)

    def on_key(self, event) -> None:  # type: ignore[override]
        focused = self.focused
        if event.key == "escape" and getattr(focused, "id", None) == "api-key-input":
            self._api_key = ""
            self.call_after_refresh(self._advance_with_summary, "✓ API key   skipped", 3)

    async def _advance_with_summary(self, summary_text: str, next_step: int) -> None:
        await self._append_summary(summary_text)
        self.current_step = next_step

    def _finish(self, model: str) -> None:
        keys: dict[str, str] = {}
        if self._api_key and self._selected_provider != "ollama":
            _, _, env_key = next(p for p in _PROVIDERS if p[0] == self._selected_provider)
            if env_key:
                keys[env_key] = self._api_key

        config_mod.save_user_config(keys, model)
        config_mod.load_user_config()

        self.app.switch_screen(MainScreen())
```

- [ ] **Step 2: Run the setup flow tests**

```bash
cd /home/zengs/data/code/ProteinClaw
pytest tests/proteinclaw/tui/test_screens.py -k "setup_flow" -v 2>&1 | tail -25
```

Expected: all 9 `test_setup_flow_*` tests PASS.

If `test_setup_flow_provider_summary_visible_after_selection` or `test_setup_flow_api_key_summary_visible_after_submission` fail with `NoMatches` for `#summaries`, check that `compose()` yields `Vertical(id="summaries")` before the card.

If the summary tests fail because `Label` objects are found but texts don't match, add an extra `await pilot.pause()` before querying — `call_after_refresh` schedules on the next refresh cycle.

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v 2>&1 | tail -15
```

Expected: all tests PASS (77 existing + 2 new = 79 total).

- [ ] **Step 4: Commit**

```bash
git add proteinclaw/cli/tui/screens/setup.py tests/proteinclaw/tui/test_screens.py
git commit -m "feat: redesign setup screen to Codex B2 style (completed steps stack above card)"
```

---

## Self-Review

**Spec coverage:**
- [x] State 1 — provider Select, action title "Choose a provider", helper text — Task 2 `_render_step` step 1
- [x] State 2 — API key Input, action title "Enter your X API key", helper text "Provider: X" — Task 2 `_render_step` step 2
- [x] State 3 — model Select, action title "Choose a default model", helper text "Provider: X" — Task 2 `_render_step` step 3
- [x] Selecting provider immediately advances — `on_select_changed` with `call_after_refresh`
- [x] Ollama skips State 2 — `current_step = 3` in `_advance_with_summary`
- [x] Escape skips API key — `on_key` → `_advance_with_summary("✓ API key   skipped", 3)`
- [x] Completed steps visible above card — `_append_summary` mounts into `#summaries`
- [x] Card wraps only current step — `#card` contains `#action-title`, `#card-content`, `#helper-text`
- [x] Footer hint varies per step — `footer_hint.update(...)` in `_render_step`
- [x] `save_user_config` / `load_user_config` / `switch_screen` sequence — `_finish()` unchanged
- [x] Provider summary text format — `✓ Provider  {name}` in `on_select_changed`
- [x] API key summary: "entered" vs "skipped" — `on_input_submitted` and `on_key`
- [x] Tests updated: `#action-title` query — Task 1 Step 1
- [x] Tests added: summary visibility — Task 1 Step 2

**Type consistency:**
- `_display_name(provider_id: str) -> str` defined at module level, used in `_render_step` and `on_select_changed`
- `_advance_with_summary(summary_text: str, next_step: int)` defined as `async def`, called via `call_after_refresh`
- `_append_summary(text: str)` defined as `async def`, called only from `_advance_with_summary`
- All widget IDs consistent: `#summaries`, `#card`, `#card-content`, `#action-title`, `#helper-text`, `#footer-hint`
