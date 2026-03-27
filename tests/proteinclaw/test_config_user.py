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


def test_needs_setup_true_for_unknown_provider(monkeypatch):
    """Model with a provider not in _PROVIDER_KEY_MAP should return True."""
    monkeypatch.setenv("DEFAULT_MODEL", "not-a-real-model")
    with patch.object(config_mod, "settings", config_mod.Settings()):
        assert needs_setup() is True
