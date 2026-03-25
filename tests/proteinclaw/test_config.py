import os
import pytest
from proteinclaw.core.config import Settings, SUPPORTED_MODELS

def test_supported_models_contains_required_keys():
    required = {"gpt-4o", "claude-opus-4-5", "deepseek-chat", "deepseek-reasoner",
                "minimax-text-01", "ollama/llama3"}
    assert required.issubset(set(SUPPORTED_MODELS.keys()))

def test_supported_models_have_provider():
    for name, cfg in SUPPORTED_MODELS.items():
        assert "provider" in cfg, f"{name} missing 'provider'"

def test_settings_default_model(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL", "gpt-4o")
    s = Settings()
    assert s.default_model == "gpt-4o"

def test_settings_default_model_fallback(monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)
    s = Settings()
    assert s.default_model in SUPPORTED_MODELS
