import json
import tempfile
from pathlib import Path
from proteinclaw.core.nanobot.config import init_nanobot_workspace, build_nanobot_config


def test_init_creates_workspace_and_soul():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "nanobot-workspace"
        init_nanobot_workspace(workspace)
        assert workspace.is_dir()
        soul = workspace / "SOUL.md"
        assert soul.exists()
        assert "ProteinClaw" in soul.read_text()


def test_build_config_anthropic():
    cfg = build_nanobot_config(
        model="claude-opus-4-5",
        workspace=Path("/tmp/ws"),
        api_key="sk-ant-test",
    )
    assert cfg["agents"]["defaults"]["model"] == "claude-opus-4-5"
    assert cfg["agents"]["defaults"]["provider"] == "anthropic"
    assert cfg["providers"]["anthropic"]["apiKey"] == "sk-ant-test"
    assert cfg["tools"]["web"]["enable"] is False
    assert cfg["tools"]["exec"]["enable"] is False


def test_build_config_openai():
    cfg = build_nanobot_config(
        model="gpt-4o",
        workspace=Path("/tmp/ws"),
        api_key="sk-openai-test",
    )
    assert cfg["agents"]["defaults"]["provider"] == "openai"
    assert cfg["providers"]["openai"]["apiKey"] == "sk-openai-test"
