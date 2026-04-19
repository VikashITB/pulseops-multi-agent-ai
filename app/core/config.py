from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal[
        "development",
        "staging",
        "production",
    ] = "development"

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    app_secret_key: str = "change-me"

    # LLM
    llm_provider: Literal[
        "openai",
        "groq",
        "gemini",
    ] = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Redis / Queue
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Agent Runtime
    agent_max_retries: int = Field(default=2, ge=1)
    agent_retry_base_delay: float = Field(default=0.5, ge=0.1)
    agent_timeout: int = Field(default=60, ge=5)

    # Batching
    max_batch_size: int = Field(default=10, ge=1)
    batch_flush_interval: float = Field(default=5.0, ge=0.5)

    # Frontend
    cors_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001,"
        "http://localhost:8000"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.cors_origins.split(",")
            if item.strip()
        ]

    @property
    def active_api_key(self) -> str:
        return {
            "openai": self.openai_api_key,
            "groq": self.groq_api_key,
            "gemini": self.gemini_api_key,
        }[self.llm_provider]

    @property
    def active_model(self) -> str:
        return {
            "openai": self.openai_model,
            "groq": self.groq_model,
            "gemini": self.gemini_model,
        }[self.llm_provider]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()