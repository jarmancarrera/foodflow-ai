import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "FoodFlow AI"
    version: str = "1.0.0"

    demo_token: str = os.getenv("FOODFLOW_DEMO_TOKEN", "")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("FOODFLOW_ANTHROPIC_MODEL", "claude-sonnet-4-6")

    agent_max_iters: int = int(os.getenv("FOODFLOW_AGENT_MAX_ITERS", "12"))
    agent_max_seconds: int = int(os.getenv("FOODFLOW_AGENT_MAX_SECONDS", "45"))
    max_completion_tokens: int = int(os.getenv("FOODFLOW_MAX_COMPLETION_TOKENS", "1024"))


def get_settings() -> Settings:
    return Settings()

