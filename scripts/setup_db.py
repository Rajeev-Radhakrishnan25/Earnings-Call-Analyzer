"""Database setup script. Run after docker-compose up."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import text
from src.config import get_settings
from src.database.connection import engine
from src.database.models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def create_tables() -> None:
    settings = get_settings()
    logger.info("Connecting to %s:%s", settings.postgres_host, settings.postgres_port)

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        if not result.scalar():
            raise RuntimeError("pgvector extension is required but not installed")
        logger.info("pgvector extension confirmed")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All tables created successfully")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
