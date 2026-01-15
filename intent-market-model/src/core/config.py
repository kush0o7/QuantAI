from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://intent:intent@localhost:5432/intent_db"
    baseline_window_days: int = 90
    embedding_dim: int = 256
    fixtures_path: str = "data/fixtures"
    watchlist_companies: str | None = None
    log_level: str = "INFO"
    enable_llm_scorer: bool = False
    enable_scheduler: bool = False
    scheduler_interval_hours: int = 24
    scheduler_source: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
