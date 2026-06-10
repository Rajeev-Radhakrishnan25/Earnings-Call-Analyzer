"""Async database connection management using SQLAlchemy 2.0."""

import logging
import ssl
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Neon requires SSL. When using DATABASE_URL (production),
# we pass ssl=True via connect_args for asyncpg.
_is_production = bool(settings.database_url)

_connect_args: dict = {}
if _is_production:
    # asyncpg needs an ssl context for Neon
    _ssl_context = ssl.create_default_context()
    _ssl_context.check_hostname = False
    _ssl_context.verify_mode = ssl.CERT_NONE
    _connect_args = {"ssl": _ssl_context}

engine = create_async_engine(
    settings.async_database_url,
    echo=(settings.app_env == "development" and not _is_production),
    pool_size=5 if _is_production else 10,
    max_overflow=10 if _is_production else 20,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()