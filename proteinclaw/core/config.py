from pydantic_settings import BaseSettings
from pydantic import Field


SUPPORTED_MODELS: dict[str, dict] = {
    "gpt-4o":            {"provider": "openai"},
    "claude-opus-4-5":   {"provider": "anthropic"},
    "deepseek-chat":     {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "deepseek-reasoner": {"provider": "deepseek",  "api_base": "https://api.deepseek.com"},
    "minimax-text-01":   {"provider": "openai",    "api_base": "https://api.minimax.chat/v1"},
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
