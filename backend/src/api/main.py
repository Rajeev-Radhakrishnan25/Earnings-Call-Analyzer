"""FastAPI application entry point for the Earnings Call Analyzer."""

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text

from src.config import get_settings
from src.api.routes import companies, health, query
from src.database.connection import async_session_factory, engine
from src.database.models import Base, Company

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Global seeding status so the frontend can poll it
seeding_status = {
    "in_progress": False,
    "completed": False,
    "message": "",
    "progress": 0,
    "total": 0,
}


async def auto_seed_if_empty() -> None:
    """Check if the database is empty and seed it automatically."""
    global seeding_status

    try:
        # Ensure tables exist
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)

        # Check if any companies exist
        async with async_session_factory() as session:
            result = await session.execute(select(func.count(Company.id)))
            count = result.scalar() or 0

        if count > 0:
            seeding_status["completed"] = True
            seeding_status["message"] = f"{count} companies already loaded"
            logger.info("Database has %d companies, skipping auto-seed", count)
            return

        logger.info("Database is empty, starting auto-seed...")
        seeding_status["in_progress"] = True
        seeding_status["message"] = "Generating sample transcripts..."

        # Generate seed data if it does not exist
        seed_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "sample_transcripts"
        if not seed_dir.exists() or not list(seed_dir.glob("*.json")):
            seeding_status["message"] = "Generating transcript data..."
            import subprocess
            import sys
            scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"

            # Run the S&P 500 generator
            gen_script = scripts_dir / "generate_seed_data.py"
            if gen_script.exists():
                subprocess.run([sys.executable, str(gen_script)], check=True)

            # Run the RBC generator if it exists
            rbc_script = scripts_dir / "generate_rbc_data.py"
            if rbc_script.exists():
                subprocess.run([sys.executable, str(rbc_script)], check=True)

        # Count JSON files for progress tracking
        json_files = list(seed_dir.glob("*.json"))
        seeding_status["total"] = len(json_files)

        # Import and run the ingestion pipeline
        from src.embedding.embedder import Embedder
        from src.ingestion.pipeline import ingest_from_json

        seeding_status["message"] = "Loading embedding model (first run downloads ~80MB)..."
        embedder = Embedder()

        for i, json_file in enumerate(sorted(json_files)):
            company_name = json_file.stem.replace("_transcripts", "").upper()
            seeding_status["message"] = f"Embedding {company_name} transcripts ({i+1}/{len(json_files)})..."
            seeding_status["progress"] = i + 1
            logger.info("Seeding %s (%d/%d)", company_name, i + 1, len(json_files))

            async with async_session_factory() as session:
                await ingest_from_json(session, json_file, embedder)
                await session.commit()

        seeding_status["in_progress"] = False
        seeding_status["completed"] = True
        seeding_status["message"] = f"Loaded {len(json_files)} companies successfully"
        logger.info("Auto-seed complete: %d company files processed", len(json_files))

    except Exception as exc:
        logger.error("Auto-seed failed: %s", exc, exc_info=True)
        seeding_status["in_progress"] = False
        seeding_status["message"] = f"Seeding failed: {str(exc)}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting Earnings Call Analyzer API")
    # Start auto-seed in background (does not block the API)
    asyncio.create_task(auto_seed_if_empty())
    yield
    logger.info("Shutting down Earnings Call Analyzer API")


app = FastAPI(
    title="Earnings Call Analyzer",
    description="RAG-based financial analysis tool for SEC EDGAR earnings call transcripts",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(companies.router, prefix="/api", tags=["companies"])
app.include_router(query.router, prefix="/api", tags=["query"])


@app.get("/api/seeding-status")
async def get_seeding_status() -> dict:
    """Returns the current auto-seed progress for the frontend."""
    return seeding_status
