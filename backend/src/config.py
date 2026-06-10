"""
Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check all configuration
at startup. If a required variable is missing, the app fails fast
with a clear error rather than crashing mid-request.

Supports two database connection modes:
    1. DATABASE_URL (single string, used by Neon/Render in production)
    2. Individual POSTGRES_* variables (used for local Docker dev)
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

    # Production: single connection string from Neon
    database_url: str = ""

    # Local dev: individual components (used if database_url is empty)
    postgres_user: str = "eca_user"
    postgres_password: str = "eca_local_dev_password"
    postgres_db: str = "earnings_call_analyzer"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def async_database_url(self) -> str:
        """
        Return the async database URL for SQLAlchemy.

        If DATABASE_URL is set (production/Neon), use it directly,
        converting the scheme to postgresql+asyncpg.
        Otherwise, build it from individual POSTGRES_* variables (local dev).
        """
        if self.database_url:
            url = self.database_url
            # Neon provides postgresql:// or postgres:// URLs.
            # SQLAlchemy async needs postgresql+asyncpg://
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif not url.startswith("postgresql+asyncpg://"):
                url = f"postgresql+asyncpg://{url}"
            return url

        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Return a sync database URL (used for scripts)."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            elif url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url

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