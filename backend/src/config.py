"""
Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check all configuration
at startup. If a required variable is missing, the app fails fast
with a clear error rather than crashing mid-request.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Earnings Call Analyzer."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_user: str = "eca_user"
    postgres_password: str = "eca_local_dev_password"
    postgres_db: str = "earnings_call_analyzer"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    anthropic_api_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    edgar_user_agent: str = "EarningsCallAnalyzer dev@example.com"
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
