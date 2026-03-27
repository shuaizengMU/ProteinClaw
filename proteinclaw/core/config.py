from pydantic_settings import BaseSettings
from pydantic import Field
import os
import tomllib
from pathlib import Path


SUPPORTED_MODELS: dict[str, dict] = {
    "gpt-4o":            {"provider": "openai"},
    "claude-opus-4-5":   {"provider": "anthropic"},
    "deepseek-chat":     {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner": {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "minimax-text-01":   {"provider": "minimax",   "api_base": "https://api.minimax.chat/v1"},
    "ollama/llama3":     {"provider": "ollama",    "api_base": "http://localhost:11434"},
}


class Settings(BaseSettings):
    default_model: str = Field(default="gpt-4o", alias="DEFAULT_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    ncbi_api_key: str = Field(default="", alias="NCBI_API_KEY")

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()


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
        return   # nothing to inject; settings is already constructed
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
    key_value = os.environ.get(env_alias, "")
    return not bool(key_value)
