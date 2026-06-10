"""
Company management API routes.

Handles company search, ingestion triggers, and dataset statistics.
"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CompanyResponse,
    CompanySearchResult,
    StatsResponse,
)
from src.database.connection import async_session_factory, get_db_session
from src.database.models import Chunk, Company, IngestionStatus, Transcript
from src.embedding.embedder import Embedder
from src.ingestion.edgar_client import EdgarClient
from src.ingestion.pipeline import ingest_company, ingest_seed_directory

logger = logging.getLogger(__name__)

router = APIRouter()

# Track ingestion status per ticker
ingestion_tracker: dict[str, dict] = {}


def get_embedder() -> Embedder:
    return Embedder()


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    session: AsyncSession = Depends(get_db_session),
) -> list[CompanyResponse]:
    """List all companies in the database with transcript counts."""
    result = await session.execute(
        select(
            Company,
            func.count(Transcript.id).label("transcript_count"),
        )
        .outerjoin(Transcript, Company.id == Transcript.company_id)
        .group_by(Company.id)
        .order_by(Company.ticker)
    )

    companies = []
    for row in result.all():
        company = row[0]
        count = row[1]
        companies.append(
            CompanyResponse(
                id=company.id,
                ticker=company.ticker,
                name=company.name,
                cik_number=company.cik_number,
                sector=company.sector,
                exchange=company.exchange,
                is_sp500=company.is_sp500,
                ingestion_status=company.ingestion_status.value,
                transcript_count=count,
                created_at=company.created_at,
            )
        )

    return companies


@router.get("/companies/search", response_model=list[CompanySearchResult])
async def search_company(
    q: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
) -> list[CompanySearchResult]:
    """Search for a company in the local database and SEC EDGAR."""
    results: list[CompanySearchResult] = []
    seen_tickers: set[str] = set()

    # Search local database first
    local_result = await session.execute(
        select(Company).where(
            (Company.ticker.ilike(f"%{q}%")) | (Company.name.ilike(f"%{q}%"))
        )
    )
    for company in local_result.scalars():
        results.append(
            CompanySearchResult(
                name=company.name,
                ticker=company.ticker,
                cik_number=company.cik_number or "",
                exchange=company.exchange,
                already_loaded=True,
            )
        )
        seen_tickers.add(company.ticker)

    # Search EDGAR for additional results
    try:
        async with EdgarClient() as client:
            edgar_results = await client.search_company(q)
            for ec in edgar_results[:10]:
                if ec.ticker not in seen_tickers:
                    results.append(
                        CompanySearchResult(
                            name=ec.name,
                            ticker=ec.ticker,
                            cik_number=ec.cik,
                            exchange=ec.exchange,
                            already_loaded=False,
                        )
                    )
                    seen_tickers.add(ec.ticker)
    except Exception as exc:
        logger.warning("EDGAR search failed: %s", exc)

    return results[:20]


@router.post("/companies/{ticker}/ingest")
async def ingest_company_endpoint(
    ticker: str,
) -> dict:
    """
    Trigger ingestion for a company from SEC EDGAR.

    Starts a background task that downloads, parses, chunks,
    embeds, and stores the company's earnings call transcripts.
    Returns immediately with a status tracking ID.
    """
    ticker = ticker.upper()

    # Check if already ingesting
    if ticker in ingestion_tracker and ingestion_tracker[ticker].get("in_progress"):
        return ingestion_tracker[ticker]

    # Check if already loaded
    async with async_session_factory() as session:
        result = await session.execute(
            select(Company).where(Company.ticker == ticker)
        )
        company = result.scalar_one_or_none()
        if company and company.ingestion_status == IngestionStatus.COMPLETED:
            return {
                "status": "already_loaded",
                "ticker": ticker,
                "message": f"{ticker} is already loaded",
                "in_progress": False,
            }

    # Start background ingestion
    ingestion_tracker[ticker] = {
        "status": "started",
        "ticker": ticker,
        "message": f"Starting ingestion for {ticker}...",
        "in_progress": True,
    }

    asyncio.create_task(_run_ingestion(ticker))

    return ingestion_tracker[ticker]


async def _run_ingestion(ticker: str) -> None:
    """Background task that runs the full EDGAR ingestion pipeline."""
    try:
        ingestion_tracker[ticker]["message"] = f"Searching EDGAR for {ticker}..."

        embedder = Embedder()

        async with async_session_factory() as session:
            result = await ingest_company(
                session=session,
                ticker=ticker,
                embedder=embedder,
                max_transcripts=10,
            )
            await session.commit()

        if result["transcripts_ingested"] > 0:
            ingestion_tracker[ticker] = {
                "status": "completed",
                "ticker": ticker,
                "message": (
                    f"Loaded {result['transcripts_ingested']} transcripts "
                    f"({result['chunks_created']} chunks) for {ticker}"
                ),
                "in_progress": False,
                "transcripts": result["transcripts_ingested"],
                "chunks": result["chunks_created"],
            }
        else:
            error_msg = "; ".join(result.get("errors", ["No transcripts found on EDGAR"]))
            ingestion_tracker[ticker] = {
                "status": "no_data",
                "ticker": ticker,
                "message": f"No transcript filings found for {ticker} on EDGAR. {error_msg}",
                "in_progress": False,
            }

    except Exception as exc:
        logger.error("Ingestion failed for %s: %s", ticker, exc, exc_info=True)
        ingestion_tracker[ticker] = {
            "status": "failed",
            "ticker": ticker,
            "message": f"Ingestion failed: {str(exc)}",
            "in_progress": False,
        }


@router.get("/companies/{ticker}/ingest-status")
async def get_ingest_status(ticker: str) -> dict:
    """Poll the ingestion status for a specific company."""
    ticker = ticker.upper()
    if ticker in ingestion_tracker:
        return ingestion_tracker[ticker]
    return {
        "status": "not_started",
        "ticker": ticker,
        "message": "No ingestion in progress",
        "in_progress": False,
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_db_session),
) -> StatsResponse:
    """Get dynamic statistics about the current dataset."""
    total_companies_result = await session.execute(select(func.count(Company.id)))
    total_companies = total_companies_result.scalar() or 0

    sp500_result = await session.execute(
        select(func.count(Company.id)).where(Company.is_sp500.is_(True))
    )
    sp500_count = sp500_result.scalar() or 0

    total_transcripts_result = await session.execute(select(func.count(Transcript.id)))
    total_transcripts = total_transcripts_result.scalar() or 0

    total_chunks_result = await session.execute(select(func.count(Chunk.id)))
    total_chunks = total_chunks_result.scalar() or 0

    quarters_result = await session.execute(
        select(
            func.count(
                func.distinct(func.concat(Transcript.year, "-", Transcript.quarter))
            )
        )
    )
    quarters_covered = quarters_result.scalar() or 0

    oldest_result = await session.execute(
        select(Transcript.quarter, Transcript.year)
        .order_by(Transcript.year, Transcript.quarter)
        .limit(1)
    )
    oldest = oldest_result.first()

    newest_result = await session.execute(
        select(Transcript.quarter, Transcript.year)
        .order_by(Transcript.year.desc(), Transcript.quarter.desc())
        .limit(1)
    )
    newest = newest_result.first()

    return StatsResponse(
        total_transcripts=total_transcripts,
        total_companies=total_companies,
        total_chunks=total_chunks,
        quarters_covered=quarters_covered,
        sp500_companies=sp500_count,
        other_companies=total_companies - sp500_count,
        oldest_quarter=f"{oldest[0]} {oldest[1]}" if oldest else None,
        newest_quarter=f"{newest[0]} {newest[1]}" if newest else None,
    )
