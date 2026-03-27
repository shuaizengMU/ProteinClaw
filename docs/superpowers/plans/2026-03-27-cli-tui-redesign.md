# CLI/TUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the ProteinClaw TUI into a modular Screen/Widget architecture, add a first-run API key setup wizard, and ensure the package installs cleanly via `uv tool install proteinclaw`.

**Architecture:** The existing monolithic `proteinclaw/cli/app.py` is split: query mode stays in `app.py` as a thin router, and the TUI moves into a new `proteinclaw/cli/tui/` sub-package. The TUI uses Textual Screens (`SetupScreen`, `MainScreen`) and reusable Widgets (`StatusBar`, `ConversationWidget`, `ToolCard`). Config management gains three new functions (`load_user_config`, `save_user_config`, `needs_setup`) that read/write `~/.config/proteinclaw/config.toml` and refresh the pydantic-settings singleton.

**Tech Stack:** Python 3.11+, Textual 0.50+, pydantic-settings, tomllib (stdlib), pytest + pytest-asyncio

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `pyproject.toml` | Move textual to main deps; add URLs metadata |
| Modify | `proteinclaw/core/config.py` | Add `CONFIG_PATH`, `load_user_config`, `save_user_config`, `needs_setup` |
| Modify | `proteinclaw/cli/app.py` | Replace inline TUI with `from proteinclaw.cli.tui.app import ProteinClawApp` |
| Create | `proteinclaw/cli/tui/__init__.py` | Package marker |
| Create | `proteinclaw/cli/tui/app.py` | `ProteinClawApp(App)` — top-level Textual app, mounts first screen |
| Create | `proteinclaw/cli/tui/screens/__init__.py` | Package marker |
| Create | `proteinclaw/cli/tui/screens/setup.py` | `SetupScreen` — first-run wizard |
| Create | `proteinclaw/cli/tui/screens/main.py` | `MainScreen` — three-zone chat interface |
| Create | `proteinclaw/cli/tui/widgets/__init__.py` | Package marker |
| Create | `proteinclaw/cli/tui/widgets/tool_card.py` | `ToolCard` — inline bordered tool call display |
| Create | `proteinclaw/cli/tui/widgets/status_bar.py` | `StatusBar` — model name + agent state |
| Create | `proteinclaw/cli/tui/widgets/conversation.py` | `ConversationWidget` — scrollable conversation area |
| Create | `tests/proteinclaw/test_config_user.py` | Tests for new config functions |
| Create | `tests/proteinclaw/tui/__init__.py` | Package marker |
| Create | `tests/proteinclaw/tui/test_widgets.py` | Textual pilot tests for widgets and screens |

---

## Task 1: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

No tests needed — this is package metadata.

- [ ] **Step 1: Move textual to main dependencies and add project URLs**

Open `pyproject.toml`. Make these changes:

1. Remove `textual>=0.50` from `[project.optional-dependencies] cli`
2. Add `textual>=0.50` to `[project.dependencies]`
3. Add `[project.urls]` section after `[project]`

```toml
[project]
name = "proteinclaw"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "litellm>=1.40",
    "httpx>=0.27",
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "python-dotenv>=1.0",
    "textual>=0.50",
]

[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/ProteinClaw"
Repository = "https://github.com/YOUR_USERNAME/ProteinClaw"

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
    "httpx[ws]>=0.27",
    "respx>=0.21",
]
```

(Replace `YOUR_USERNAME` with the actual GitHub username.)

Remove the now-empty `cli` section from `[project.optional-dependencies]` entirely.

- [ ] **Step 2: Verify install resolves without error**

```bash
uv pip install -e . --dry-run
```

Expected: dependency resolution succeeds, `textual` appears in the resolved set.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: move textual to main deps, add project URLs"
```

---

## Task 2: Add config management functions

**Files:**
- Modify: `proteinclaw/core/config.py`
- Create: `tests/proteinclaw/test_config_user.py`

The existing `Settings` class and `SUPPORTED_MODELS` dict are unchanged. Three new functions and a `CONFIG_PATH` constant are added.

- [ ] **Step 1: Write the failing tests**

Create `tests/proteinclaw/test_config_user.py`:

```python
from __future__ import annotations
import os
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

import proteinclaw.core.config as config_mod
from proteinclaw.core.config import (
    load_user_config,
    save_user_config,
    needs_setup,
)


# ── save_user_config ──────────────────────────────────────────────────────────

def test_save_creates_file(tmp_path):
    config_file = tmp_path / "config.toml"
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        save_user_config({"ANTHROPIC_API_KEY": "sk-test"}, "claude-opus-4-5")
    assert config_file.exists()


def test_save_writes_key_and_model(tmp_path):
    config_file = tmp_path / "config.toml"
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        save_user_config({"DEEPSEEK_API_KEY": "ds-abc"}, "deepseek-chat")
    with open(config_file, "rb") as f:
        data = tomllib.load(f)
    assert data["keys"]["DEEPSEEK_API_KEY"] == "ds-abc"
    assert data["defaults"]["model"] == "deepseek-chat"


def test_save_creates_parent_dirs(tmp_path):
    config_file = tmp_path / "sub" / "dir" / "config.toml"
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        save_user_config({}, "gpt-4o")
    assert config_file.exists()


# ── load_user_config ──────────────────────────────────────────────────────────

def test_load_injects_missing_key(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[keys]\nDEEPSEEK_API_KEY = "ds-from-file"\n')
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        load_user_config()
    assert os.environ.get("DEEPSEEK_API_KEY") == "ds-from-file"


def test_load_env_takes_priority(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[keys]\nDEEPSEEK_API_KEY = "ds-from-file"\n')
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-from-env")
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        load_user_config()
    assert os.environ["DEEPSEEK_API_KEY"] == "ds-from-env"


def test_load_skips_empty_values(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[keys]\nOPENAI_API_KEY = ""\n')
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        load_user_config()
    assert os.environ.get("OPENAI_API_KEY") is None


def test_load_missing_file_is_noop(tmp_path, monkeypatch):
    config_file = tmp_path / "nonexistent.toml"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        load_user_config()  # must not raise
    assert os.environ.get("DEEPSEEK_API_KEY") is None


def test_load_sets_default_model(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text('[defaults]\nmodel = "deepseek-chat"\n')
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    with patch.object(config_mod, "CONFIG_PATH", config_file):
        load_user_config()
    assert os.environ.get("DEFAULT_MODEL") == "deepseek-chat"


# ── needs_setup ───────────────────────────────────────────────────────────────

def test_needs_setup_true_when_no_key(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "deepseek-chat")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with patch.object(config_mod, "settings", config_mod.Settings()):
        assert needs_setup() is True


def test_needs_setup_false_when_key_present(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with patch.object(config_mod, "settings", config_mod.Settings()):
        assert needs_setup() is False


def test_needs_setup_false_for_ollama(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "ollama/llama3")
    with patch.object(config_mod, "settings", config_mod.Settings()):
        assert needs_setup() is False


def test_needs_setup_false_for_anthropic(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "claude-opus-4-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    with patch.object(config_mod, "settings", config_mod.Settings()):
        assert needs_setup() is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/test_config_user.py -v
```

Expected: ImportError — `load_user_config`, `save_user_config`, `needs_setup` not yet defined.

- [ ] **Step 3: Implement the config functions**

Add to the bottom of `proteinclaw/core/config.py` (after `settings = Settings()`):

```python
import os
import tomllib
from pathlib import Path


CONFIG_PATH = Path("~/.config/proteinclaw/config.toml").expanduser()

# Maps provider name → Settings field alias (env var name)
_PROVIDER_KEY_MAP: dict[str, str] = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
    "minimax":   "MINIMAX_API_KEY",
}


def load_user_config() -> None:
    """Read ~/.config/proteinclaw/config.toml and inject any missing env vars.

    Key names in the TOML file must match the uppercase env var aliases used by
    Settings (e.g. ANTHROPIC_API_KEY). Environment variables already set take
    priority and are never overwritten.

    Reinitialises the module-level ``settings`` singleton so that the newly
    injected env vars are picked up (pydantic_settings reads env vars only at
    construction time).
    """
    global settings
    if not CONFIG_PATH.exists():
        settings = Settings()
        return
    with open(CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)
    for key, value in data.get("keys", {}).items():
        if value and key not in os.environ:
            os.environ[key] = value
    default_model = data.get("defaults", {}).get("model", "")
    if default_model and "DEFAULT_MODEL" not in os.environ:
        os.environ["DEFAULT_MODEL"] = default_model
    settings = Settings()


def save_user_config(keys: dict[str, str], default_model: str) -> None:
    """Write API keys and default model to ~/.config/proteinclaw/config.toml.

    ``keys`` must use uppercase env var alias names as keys
    (e.g. ``{"ANTHROPIC_API_KEY": "sk-ant-..."}``) and may omit providers
    the user chose to skip.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[keys]\n"]
    for k, v in keys.items():
        lines.append(f'{k} = "{v}"\n')
    lines.append("\n[defaults]\n")
    lines.append(f'model = "{default_model}"\n')
    CONFIG_PATH.write_text("".join(lines))


def needs_setup() -> bool:
    """Return True if the API key for the current default model is missing.

    Specifically, checks the key required by the provider of
    ``settings.default_model`` in ``SUPPORTED_MODELS``. Ollama requires no
    key and always returns False. Call after ``load_user_config()`` so that
    config-file keys have been injected.
    """
    provider = SUPPORTED_MODELS.get(settings.default_model, {}).get("provider", "")
    if provider == "ollama":
        return False
    env_alias = _PROVIDER_KEY_MAP.get(provider, "")
    if not env_alias:
        return True  # unknown provider — treat as not configured
    key_value = getattr(settings, env_alias.lower(), "")
    return not bool(key_value)
```

Note: `getattr(settings, env_alias.lower(), "")` works because Settings field names are lowercase versions of the aliases (e.g. `ANTHROPIC_API_KEY` → `anthropic_api_key`).

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/proteinclaw/test_config_user.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run the full test suite to check nothing broke**

```bash
pytest -v
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add proteinclaw/core/config.py tests/proteinclaw/test_config_user.py
git commit -m "feat: add load_user_config, save_user_config, needs_setup"
```

---

## Task 3: Create TUI package scaffold and __init__ files

**Files:**
- Create: `proteinclaw/cli/tui/__init__.py`
- Create: `proteinclaw/cli/tui/screens/__init__.py`
- Create: `proteinclaw/cli/tui/widgets/__init__.py`
- Create: `tests/proteinclaw/tui/__init__.py`

- [ ] **Step 1: Create empty package markers**

```bash
touch proteinclaw/cli/tui/__init__.py
touch proteinclaw/cli/tui/screens/__init__.py
touch proteinclaw/cli/tui/widgets/__init__.py
touch tests/proteinclaw/tui/__init__.py
```

- [ ] **Step 2: Verify Python can import the new packages**

```bash
python -c "import proteinclaw.cli.tui; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add proteinclaw/cli/tui/__init__.py proteinclaw/cli/tui/screens/__init__.py \
        proteinclaw/cli/tui/widgets/__init__.py tests/proteinclaw/tui/__init__.py
git commit -m "chore: scaffold tui sub-package directories"
```

---

## Task 4: ToolCard widget

**Files:**
- Create: `proteinclaw/cli/tui/widgets/tool_card.py`
- Create: `tests/proteinclaw/tui/test_widgets.py` (initial version)

`ToolCard` is a `Widget` that shows a tool name + args on one label and a pending/filled result on a second label, enclosed in a border.

- [ ] **Step 1: Write the failing tests**

Create `tests/proteinclaw/tui/test_widgets.py`:

```python
from __future__ import annotations
import pytest
from textual.app import App, ComposeResult

from proteinclaw.cli.tui.widgets.tool_card import ToolCard


# Minimal host app for widget testing
class _ToolCardApp(App):
    def compose(self) -> ComposeResult:
        yield ToolCard("uniprot", {"id": "P04637"})


async def test_tool_card_shows_tool_name():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        # The tool name label has id="tool-name"
        label_text = str(card.query_one("#tool-name").renderable)
        assert "uniprot" in label_text


async def test_tool_card_shows_args():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        label_text = str(card.query_one("#tool-name").renderable)
        assert "P04637" in label_text


async def test_tool_card_result_initially_pending():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        result_text = str(card.query_one("#result").renderable)
        assert "..." in result_text


async def test_tool_card_set_result_updates_label():
    async with _ToolCardApp().run_test() as pilot:
        card = pilot.app.query_one(ToolCard)
        card.set_result("TP53_HUMAN, 393 aa")
        await pilot.pause()
        result_text = str(card.query_one("#result").renderable)
        assert "TP53_HUMAN" in result_text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/tui/test_widgets.py -v
```

Expected: ImportError — `ToolCard` not yet defined.

- [ ] **Step 3: Implement ToolCard**

Create `proteinclaw/cli/tui/widgets/tool_card.py`:

```python
from __future__ import annotations
import json
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label


class ToolCard(Widget):
    """Inline bordered card displaying a tool call and its result."""

    DEFAULT_CSS = """
    ToolCard {
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
        height: auto;
    }
    """

    def __init__(self, tool: str, args: dict) -> None:
        super().__init__()
        self._tool = tool
        self._args = args

    def compose(self) -> ComposeResult:
        args_str = json.dumps(self._args)
        yield Label(
            f"[bold]▶ {self._tool}[/bold]  {args_str}",
            id="tool-name",
            markup=True,
        )
        yield Label("[dim]...[/dim]", id="result", markup=True)

    def set_result(self, result: object) -> None:
        """Update the result label with the observation value."""
        self.query_one("#result", Label).update(str(result))
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/proteinclaw/tui/test_widgets.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/cli/tui/widgets/tool_card.py tests/proteinclaw/tui/test_widgets.py
git commit -m "feat: add ToolCard widget"
```

---

## Task 5: StatusBar widget

**Files:**
- Create: `proteinclaw/cli/tui/widgets/status_bar.py`
- Modify: `tests/proteinclaw/tui/test_widgets.py` (append tests)

`StatusBar` displays the current model name and agent state (`ready` / `thinking...` / `error`). On `error`, it auto-resets to `ready` after 3 seconds.

- [ ] **Step 1: Append StatusBar tests to test_widgets.py**

Add the following to the bottom of `tests/proteinclaw/tui/test_widgets.py`:

```python
from proteinclaw.cli.tui.widgets.status_bar import StatusBar


class _StatusBarApp(App):
    def compose(self) -> ComposeResult:
        yield StatusBar("deepseek-chat")


async def test_status_bar_shows_model():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        label_text = str(bar.query_one("#status-label").renderable)
        assert "deepseek-chat" in label_text


async def test_status_bar_initial_state_ready():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        label_text = str(bar.query_one("#status-label").renderable)
        assert "ready" in label_text


async def test_status_bar_set_state_thinking():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        bar.set_state("thinking")
        await pilot.pause()
        label_text = str(bar.query_one("#status-label").renderable)
        assert "thinking" in label_text


async def test_status_bar_set_model():
    async with _StatusBarApp().run_test() as pilot:
        bar = pilot.app.query_one(StatusBar)
        bar.set_model("gpt-4o")
        await pilot.pause()
        label_text = str(bar.query_one("#status-label").renderable)
        assert "gpt-4o" in label_text
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/proteinclaw/tui/test_widgets.py -k "status_bar" -v
```

Expected: ImportError — `StatusBar` not yet defined.

- [ ] **Step 3: Implement StatusBar**

Create `proteinclaw/cli/tui/widgets/status_bar.py`:

```python
from __future__ import annotations
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class StatusBar(Widget):
    """Top status bar showing model name and agent state."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
        dock: top;
    }
    """

    state: reactive[str] = reactive("ready")

    def __init__(self, model: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model

    def compose(self) -> ComposeResult:
        yield Label(self._format(), id="status-label")

    def _format(self) -> str:
        return f"ProteinClaw ── model: {self._model} ── {self.state}"

    def watch_state(self, _value: str) -> None:
        if self.is_mounted:
            self.query_one("#status-label", Label).update(self._format())

    def set_state(self, state: str, message: str = "") -> None:
        """Set the agent state. 'error' auto-resets to 'ready' after 3 seconds."""
        self.state = state
        if state == "error":
            self.set_timer(3.0, lambda: self.set_state("ready"))

    def set_model(self, model: str) -> None:
        """Update the displayed model name."""
        self._model = model
        if self.is_mounted:
            self.query_one("#status-label", Label).update(self._format())
```

- [ ] **Step 4: Run all widget tests to verify they pass**

```bash
pytest tests/proteinclaw/tui/test_widgets.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/cli/tui/widgets/status_bar.py tests/proteinclaw/tui/test_widgets.py
git commit -m "feat: add StatusBar widget"
```

---

## Task 6: ConversationWidget

**Files:**
- Create: `proteinclaw/cli/tui/widgets/conversation.py`
- Modify: `tests/proteinclaw/tui/test_widgets.py` (append tests)

`ConversationWidget` extends `VerticalScroll`. It accumulates conversation content by mounting child widgets: `Static` for text (user queries, tokens, thinking) and `ToolCard` for tool calls. A `_pending_card` pointer routes `ObservationEvent` results to the correct card.

- [ ] **Step 1: Append ConversationWidget tests**

Add to the bottom of `tests/proteinclaw/tui/test_widgets.py`:

```python
from proteinclaw.cli.tui.widgets.conversation import ConversationWidget


class _ConvApp(App):
    def compose(self) -> ComposeResult:
        yield ConversationWidget(id="conv")


async def test_conversation_append_thinking_mounts_widget():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        assert len(conv.children) == 0
        conv.append_thinking("planning next step")
        await pilot.pause()
        assert len(conv.children) == 1


async def test_conversation_append_token_accumulates():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.append_token("Hello")
        conv.append_token(", world")
        await pilot.pause()
        # Only one Static widget for the whole streamed response
        assert len(conv.children) == 1


async def test_conversation_add_tool_card_sets_pending():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.add_tool_card("uniprot", {"id": "P04637"})
        await pilot.pause()
        assert conv._pending_card is not None
        assert isinstance(conv._pending_card, ToolCard)


async def test_conversation_complete_tool_card_clears_pending():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.add_tool_card("uniprot", {"id": "P04637"})
        await pilot.pause()
        conv.complete_tool_card("TP53_HUMAN")
        assert conv._pending_card is None


async def test_conversation_tool_card_new_response_resets_buffer():
    """append_token after add_tool_card creates a new Static, not appending to old buffer."""
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.append_token("before tool")
        await pilot.pause()
        conv.add_tool_card("blast", {"sequence": "MKTII"})
        await pilot.pause()
        conv.append_token("after tool")
        await pilot.pause()
        # Should have: 1 Static (before), 1 ToolCard, 1 Static (after) = 3 children
        assert len(conv.children) == 3


async def test_conversation_clear_removes_all_children():
    async with _ConvApp().run_test() as pilot:
        conv = pilot.app.query_one(ConversationWidget)
        conv.append_token("hello")
        conv.add_tool_card("uniprot", {"id": "P04637"})
        await pilot.pause()
        conv.clear_conversation()
        await pilot.pause()
        assert len(conv.children) == 0
        assert conv._pending_card is None
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/proteinclaw/tui/test_widgets.py -k "conversation" -v
```

Expected: ImportError — `ConversationWidget` not yet defined.

- [ ] **Step 3: Implement ConversationWidget**

Create `proteinclaw/cli/tui/widgets/conversation.py`:

```python
from __future__ import annotations
from textual.containers import VerticalScroll
from textual.widgets import Static

from proteinclaw.cli.tui.widgets.tool_card import ToolCard


class ConversationWidget(VerticalScroll):
    """Scrollable conversation area with mixed Static text and ToolCard children."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._pending_card: ToolCard | None = None
        self._current_response: Static | None = None
        self._response_buffer: list[str] = []

    def append_thinking(self, content: str) -> None:
        """Mount a dim italic Static for a ThinkingEvent. Not added to history."""
        self._current_response = None
        self._response_buffer = []
        self.mount(Static(f"[dim italic]{content}[/dim italic]", markup=True))
        self.scroll_end(animate=False)

    def append_token(self, content: str) -> None:
        """Append a token to the current response Static, creating it if needed."""
        if self._current_response is None:
            self._current_response = Static("", markup=False)
            self.mount(self._current_response)
            self._response_buffer = []
        self._response_buffer.append(content)
        self._current_response.update("".join(self._response_buffer))
        self.scroll_end(animate=False)

    def add_tool_card(self, tool: str, args: dict) -> None:
        """Mount a new ToolCard and set it as the pending card for the next result."""
        self._current_response = None
        self._response_buffer = []
        card = ToolCard(tool, args)
        self.mount(card)
        self._pending_card = card
        self.scroll_end(animate=False)

    def complete_tool_card(self, result: object) -> None:
        """Route an ObservationEvent result to the pending ToolCard, then clear it."""
        if self._pending_card is not None:
            self._pending_card.set_result(result)
            self._pending_card = None

    def clear_conversation(self) -> None:
        """Remove all children and reset internal state."""
        self.remove_children()
        self._pending_card = None
        self._current_response = None
        self._response_buffer = []
```

- [ ] **Step 4: Run all widget tests**

```bash
pytest tests/proteinclaw/tui/test_widgets.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/cli/tui/widgets/conversation.py tests/proteinclaw/tui/test_widgets.py
git commit -m "feat: add ConversationWidget"
```

---

## Task 7: SetupScreen

**Files:**
- Create: `proteinclaw/cli/tui/screens/setup.py`
- Create: `tests/proteinclaw/tui/test_screens.py`

`SetupScreen` shows Input fields for each API key, a Select for default model, and a Save button. On mount, it pre-fills any keys already in the environment. On save, it calls `save_user_config()`, reloads `settings`, and calls `app.switch_screen(MainScreen())`.

- [ ] **Step 1: Write the failing tests**

Create `tests/proteinclaw/tui/test_screens.py`:

```python
from __future__ import annotations
import os
from unittest.mock import patch, MagicMock

import pytest
from textual.app import App, ComposeResult

import proteinclaw.core.config as config_mod
from proteinclaw.cli.tui.screens.setup import SetupScreen


class _SetupApp(App):
    """Minimal host that starts on SetupScreen."""

    def on_mount(self) -> None:
        self.switch_screen(SetupScreen())


async def test_setup_screen_shows_key_inputs():
    async with _SetupApp().run_test() as pilot:
        # All four key input fields must be present
        from textual.widgets import Input
        inputs = pilot.app.query(Input)
        input_ids = {inp.id for inp in inputs}
        assert "ANTHROPIC_API_KEY" in input_ids
        assert "DEEPSEEK_API_KEY" in input_ids


async def test_setup_screen_prefills_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-prefill")
    async with _SetupApp().run_test() as pilot:
        from textual.widgets import Input
        field = pilot.app.query_one("#ANTHROPIC_API_KEY", Input)
        assert field.value == "sk-ant-prefill"


async def test_setup_screen_save_calls_save_user_config():
    saved: list[tuple] = []

    def _fake_save(keys, model):
        saved.append((keys, model))

    with patch.object(config_mod, "save_user_config", _fake_save), \
         patch.object(config_mod, "Settings", config_mod.Settings):
        async with _SetupApp().run_test() as pilot:
            from textual.widgets import Input, Button
            pilot.app.query_one("#DEEPSEEK_API_KEY", Input).value = "ds-test"
            await pilot.click("#save-btn")
            await pilot.pause()

    assert len(saved) == 1
    assert saved[0][0].get("DEEPSEEK_API_KEY") == "ds-test"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/proteinclaw/tui/test_screens.py -v
```

Expected: ImportError — `SetupScreen` not yet defined.

- [ ] **Step 3: Implement SetupScreen**

Create `proteinclaw/cli/tui/screens/setup.py`:

```python
from __future__ import annotations
import os

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select

import proteinclaw.core.config as config_mod
from proteinclaw.core.config import SUPPORTED_MODELS, save_user_config


_KEY_FIELDS: list[tuple[str, str]] = [
    ("ANTHROPIC_API_KEY", "Anthropic API Key"),
    ("OPENAI_API_KEY", "OpenAI API Key"),
    ("DEEPSEEK_API_KEY", "DeepSeek API Key"),
    ("MINIMAX_API_KEY", "MiniMax API Key"),
]


class SetupScreen(Screen):
    """First-run API key configuration wizard."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #setup-container {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }
    Label {
        margin: 0 0 0 0;
    }
    Input {
        margin: 0 0 1 0;
    }
    Button {
        margin: 1 0 0 0;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-container"):
            yield Label("Welcome to ProteinClaw!\nLet's configure your API keys.\n")
            for env_key, display_label in _KEY_FIELDS:
                yield Label(f"{display_label}:")
                yield Input(
                    placeholder=f"{display_label} (press Enter to skip)",
                    password=True,
                    id=env_key,
                )
            yield Label("\nDefault model:")
            yield Select(
                [(m, m) for m in SUPPORTED_MODELS],
                value="deepseek-chat",
                id="default-model",
            )
            yield Button("Save & Continue", variant="primary", id="save-btn")

    def on_mount(self) -> None:
        """Pre-fill any API key fields that are already in the environment."""
        for env_key, _ in _KEY_FIELDS:
            value = os.environ.get(env_key, "")
            if value:
                self.query_one(f"#{env_key}", Input).value = value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save-btn":
            return

        keys: dict[str, str] = {}
        for env_key, _ in _KEY_FIELDS:
            value = self.query_one(f"#{env_key}", Input).value.strip()
            if value:
                keys[env_key] = value

        model_select = self.query_one("#default-model", Select)
        default_model = str(model_select.value) if model_select.value else "deepseek-chat"

        save_user_config(keys, default_model)

        # Reinitialise settings so the saved keys take effect immediately
        config_mod.settings = config_mod.Settings()

        # Import here to avoid circular import at module level
        from proteinclaw.cli.tui.screens.main import MainScreen
        self.app.switch_screen(MainScreen())
```

- [ ] **Step 4: Run screen tests**

```bash
pytest tests/proteinclaw/tui/test_screens.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/cli/tui/screens/setup.py tests/proteinclaw/tui/test_screens.py
git commit -m "feat: add SetupScreen first-run wizard"
```

---

## Task 8: MainScreen

**Files:**
- Create: `proteinclaw/cli/tui/screens/main.py`
- Modify: `tests/proteinclaw/tui/test_screens.py` (append tests)

`MainScreen` composes `StatusBar` + `ConversationWidget` + `Input`. It handles agent streaming via an async event loop and slash commands.

- [ ] **Step 1: Append MainScreen tests**

Add to the bottom of `tests/proteinclaw/tui/test_screens.py`:

```python
from unittest.mock import AsyncMock, patch
from proteinclaw.cli.tui.screens.main import MainScreen
from proteinclaw.core.agent.events import TokenEvent, DoneEvent, ErrorEvent, ToolCallEvent, ObservationEvent
from proteinclaw.cli.tui.widgets.status_bar import StatusBar
from proteinclaw.cli.tui.widgets.conversation import ConversationWidget


class _MainApp(App):
    def on_mount(self) -> None:
        self.switch_screen(MainScreen())


async def test_main_screen_layout_has_required_widgets():
    async with _MainApp().run_test() as pilot:
        from textual.widgets import Input
        pilot.app.query_one(StatusBar)      # must not raise
        pilot.app.query_one(ConversationWidget)
        pilot.app.query_one(Input)


async def test_main_screen_clear_command():
    async with _MainApp().run_test() as pilot:
        from textual.widgets import Input
        inp = pilot.app.query_one(Input)
        inp.value = "/clear"
        await pilot.press("enter")
        await pilot.pause()
        conv = pilot.app.query_one(ConversationWidget)
        assert len(conv.children) == 0


async def test_main_screen_unknown_command_shows_message():
    async with _MainApp().run_test() as pilot:
        from textual.widgets import Input
        inp = pilot.app.query_one(Input)
        inp.value = "/notacommand"
        await pilot.press("enter")
        await pilot.pause()
        conv = pilot.app.query_one(ConversationWidget)
        assert len(conv.children) > 0


async def test_main_screen_model_command_switches_model():
    async with _MainApp().run_test() as pilot:
        from textual.widgets import Input
        inp = pilot.app.query_one(Input)
        inp.value = "/model deepseek-chat"
        await pilot.press("enter")
        await pilot.pause()
        bar = pilot.app.query_one(StatusBar)
        assert "deepseek-chat" in str(bar.query_one("#status-label").renderable)


async def test_main_screen_streams_token_events():
    """Agent run that emits tokens ends with content in ConversationWidget."""

    async def _fake_run(query, history, model):
        yield TokenEvent(content="Hello")
        yield TokenEvent(content=" world")
        yield DoneEvent()

    with patch("proteinclaw.cli.tui.screens.main.run", side_effect=_fake_run):
        async with _MainApp().run_test() as pilot:
            from textual.widgets import Input
            inp = pilot.app.query_one(Input)
            inp.value = "What is P04637?"
            await pilot.press("enter")
            await pilot.pause(delay=0.1)
            conv = pilot.app.query_one(ConversationWidget)
            # At least one Static with content
            assert len(conv.children) >= 1
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/proteinclaw/tui/test_screens.py -k "main_screen" -v
```

Expected: ImportError — `MainScreen` not yet defined.

- [ ] **Step 3: Implement MainScreen**

Create `proteinclaw/cli/tui/screens/main.py`:

```python
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Static

from proteinclaw.core.agent.events import (
    DoneEvent, ErrorEvent, ObservationEvent,
    ThinkingEvent, TokenEvent, ToolCallEvent,
)
from proteinclaw.core.agent.loop import run
from proteinclaw.core.config import SUPPORTED_MODELS, settings
from proteinclaw.cli.tui.widgets.conversation import ConversationWidget
from proteinclaw.cli.tui.widgets.status_bar import StatusBar


class MainScreen(Screen):
    """Three-zone conversation interface: status bar + conversation + input."""

    CSS = """
    MainScreen {
        layout: vertical;
    }
    Input {
        dock: bottom;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, model: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model or settings.default_model
        self._history: list[dict] = []

    def compose(self) -> ComposeResult:
        yield StatusBar(self._model, id="status")
        yield ConversationWidget(id="conversation")
        yield Input(
            placeholder="Ask ProteinClaw... (/model /tools /clear /exit)",
            id="input",
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        self.query_one("#input", Input).value = ""
        if not query:
            return

        if query.startswith("/"):
            await self._handle_command(query)
            return

        conv = self.query_one("#conversation", ConversationWidget)
        status = self.query_one("#status", StatusBar)

        conv.mount(Static(f"[bold blue]> {query}[/bold blue]", markup=True))
        self._history.append({"role": "user", "content": query})

        response_tokens: list[str] = []
        first_event = True

        async for ev in run(query=query, history=self._history[:-1], model=self._model):
            if first_event:
                status.set_state("thinking")
                first_event = False

            if isinstance(ev, ThinkingEvent):
                conv.append_thinking(ev.content)
            elif isinstance(ev, TokenEvent):
                conv.append_token(ev.content)
                response_tokens.append(ev.content)
            elif isinstance(ev, ToolCallEvent):
                conv.add_tool_card(ev.tool, ev.args)
            elif isinstance(ev, ObservationEvent):
                conv.complete_tool_card(ev.result)
            elif isinstance(ev, DoneEvent):
                status.set_state("ready")
            elif isinstance(ev, ErrorEvent):
                status.set_state("error", ev.message)
                response_tokens.append(f"[Error: {ev.message}]")

        if response_tokens:
            self._history.append(
                {"role": "assistant", "content": "".join(response_tokens)}
            )

    async def _handle_command(self, cmd: str) -> None:
        parts = cmd.split()
        conv = self.query_one("#conversation", ConversationWidget)
        status = self.query_one("#status", StatusBar)

        if parts[0] == "/clear":
            self._history = []
            conv.clear_conversation()

        elif parts[0] == "/exit":
            self.app.exit()

        elif parts[0] == "/model":
            if len(parts) < 2:
                available = ", ".join(SUPPORTED_MODELS)
                conv.mount(Static(
                    f"[yellow]Usage: /model <name>. Available: {available}[/yellow]",
                    markup=True,
                ))
            elif parts[1] in SUPPORTED_MODELS:
                self._model = parts[1]
                status.set_model(self._model)
                conv.mount(Static(
                    f"[green]Switched to model: {self._model}[/green]",
                    markup=True,
                ))
            else:
                available = ", ".join(SUPPORTED_MODELS)
                conv.mount(Static(
                    f"[red]Unknown model '{parts[1]}'. Available: {available}[/red]",
                    markup=True,
                ))

        elif parts[0] == "/tools":
            from proteinbox.tools.registry import discover_tools
            tools = discover_tools()
            for name, tool in tools.items():
                conv.mount(Static(
                    f"[cyan]{name}[/cyan]: {tool.description}",
                    markup=True,
                ))

        else:
            conv.mount(Static(
                f"[yellow]Unknown command '{parts[0]}'. Try /model /tools /clear /exit[/yellow]",
                markup=True,
            ))
```

- [ ] **Step 4: Run all screen tests**

```bash
pytest tests/proteinclaw/tui/test_screens.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add proteinclaw/cli/tui/screens/main.py tests/proteinclaw/tui/test_screens.py
git commit -m "feat: add MainScreen three-zone chat interface"
```

---

## Task 9: Wire up ProteinClawApp and update cli/app.py

**Files:**
- Create: `proteinclaw/cli/tui/app.py`
- Modify: `proteinclaw/cli/app.py`

This is the final wiring task. `ProteinClawApp` handles startup: loads config, decides which screen to show. `cli/app.py` replaces its inline TUI with a one-line import.

- [ ] **Step 1: Create proteinclaw/cli/tui/app.py**

```python
from __future__ import annotations

from textual.app import App

from proteinclaw.core.config import load_user_config, needs_setup


class ProteinClawApp(App):
    """Top-level Textual application for ProteinClaw."""

    TITLE = "ProteinClaw"

    async def on_mount(self) -> None:
        load_user_config()
        if needs_setup():
            from proteinclaw.cli.tui.screens.setup import SetupScreen
            self.switch_screen(SetupScreen())
        else:
            from proteinclaw.cli.tui.screens.main import MainScreen
            self.switch_screen(MainScreen())
```

- [ ] **Step 2: Update proteinclaw/cli/app.py**

Replace the `_run_tui()` function and remove the Textual imports that are no longer needed at the top of the file. The new `_run_tui()` is a one-liner:

Open `proteinclaw/cli/app.py`. Replace the entire `_run_tui()` function (lines 27–110 in the current file, from `def _run_tui() -> None:` through `ProteinClawApp().run()`) with:

```python
def _run_tui() -> None:
    from proteinclaw.cli.tui.app import ProteinClawApp
    ProteinClawApp().run()
```

Also remove the now-unused imports at the top:
- Remove: `from textual.app import App, ComposeResult`
- Remove: `from textual.widgets import Header, Footer, Input, RichLog`
- Remove: `from textual.binding import Binding`

Keep everything else unchanged (the `_run_query` function and `main()`).

- [ ] **Step 3: Smoke test — launch TUI from CLI entry point**

```bash
python -m proteinclaw.cli.app
```

Expected: ProteinClaw TUI launches (either SetupScreen if no API key configured, or MainScreen if env vars are set). Press Ctrl+C or type `/exit` to quit.

- [ ] **Step 4: Run the full test suite one final time**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add proteinclaw/cli/tui/app.py proteinclaw/cli/app.py
git commit -m "feat: wire up ProteinClawApp and refactor cli entry point"
```

---

## Done

After all 9 tasks are complete, `proteinclaw` can be installed and run as:

```bash
uv pip install -e .
proteinclaw                        # launches TUI (setup wizard if no key configured)
proteinclaw query "What is P04637?"  # non-interactive query mode
```
