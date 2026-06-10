"""
Ingestion pipeline orchestrator.

Coordinates the full data flow from SEC EDGAR to the database:

    1. Search EDGAR for company and transcript filings
    2. Download filing HTML
    3. Parse transcript to extract speaker turns
    4. Chunk speaker turns with metadata
    5. Generate embeddings for each chunk
    6. Store everything in PostgreSQL with pgvector

This module provides two entry points:
    - ingest_company(): Full pipeline for a single company via EDGAR
    - ingest_from_json(): Load pre-structured transcript data (for seeding)
"""

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chunking.chunker import TranscriptChunk, chunk_transcript
from src.config import get_settings
from src.database.models import (
    Chunk,
    Company,
    IngestionStatus,
    SectionType,
    SpeakerRole,
    Transcript,
)
from src.embedding.embedder import Embedder
from src.ingestion.edgar_client import EdgarClient
from src.ingestion.transcript_parser import (
    ParsedTranscript,
    parse_transcript,
    parse_transcript_from_json,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _map_section_type(section: str) -> SectionType:
    """Map string section type to the database enum."""
    mapping = {
        "prepared_remarks": SectionType.PREPARED_REMARKS,
        "qa": SectionType.QA,
    }
    return mapping.get(section, SectionType.UNKNOWN)


def _map_speaker_role(role: str) -> SpeakerRole:
    """Map string speaker role to the database enum."""
    mapping = {
        "ceo": SpeakerRole.CEO,
        "cfo": SpeakerRole.CFO,
        "coo": SpeakerRole.COO,
        "cto": SpeakerRole.CTO,
        "executive": SpeakerRole.EXECUTIVE,
        "analyst": SpeakerRole.ANALYST,
        "operator": SpeakerRole.OPERATOR,
    }
    return mapping.get(role, SpeakerRole.UNKNOWN)


async def _store_transcript_chunks(
    session: AsyncSession,
    company: Company,
    parsed: ParsedTranscript,
    chunks: list[TranscriptChunk],
    embeddings: list[list[float]],
    filing_url: str = "",
    filing_date: str = "",
    filing_type: str = "",
) -> Transcript:
    """
    Store a parsed transcript and its chunks in the database.

    Creates a Transcript record and associated Chunk records,
    each with its embedding vector.
    """
    transcript = Transcript(
        company_id=company.id,
        quarter=parsed.quarter,
        year=parsed.year,
        filing_date=filing_date,
        filing_url=filing_url,
        filing_type=filing_type,
        raw_content=parsed.raw_text[:50000] if parsed.raw_text else None,
        parsed_content=None,
        speaker_count=len(parsed.speakers),
        chunk_count=len(chunks),
    )
    session.add(transcript)
    await session.flush()  # Get the transcript ID

    for chunk_data, embedding in zip(chunks, embeddings):
        chunk = Chunk(
            transcript_id=transcript.id,
            content=chunk_data.content,
            speaker_name=chunk_data.speaker_name,
            speaker_role=_map_speaker_role(chunk_data.speaker_role),
            section_type=_map_section_type(chunk_data.section_type),
            chunk_index=chunk_data.chunk_index,
            token_count=chunk_data.token_count,
            embedding=embedding,
        )
        session.add(chunk)

    logger.info(
        "Stored transcript %s %s %d: %d chunks",
        company.ticker, parsed.quarter, parsed.year, len(chunks),
    )

    return transcript


async def get_or_create_company(
    session: AsyncSession,
    ticker: str,
    name: str,
    cik: str = "",
    sector: str = "",
    exchange: str = "",
    is_sp500: bool = False,
) -> Company:
    """Get an existing company or create a new one."""
    result = await session.execute(
        select(Company).where(Company.ticker == ticker.upper())
    )
    company = result.scalar_one_or_none()

    if company:
        return company

    company = Company(
        ticker=ticker.upper(),
        name=name,
        cik_number=cik,
        sector=sector,
        exchange=exchange,
        is_sp500=is_sp500,
        ingestion_status=IngestionStatus.PENDING,
    )
    session.add(company)
    await session.flush()
    return company


async def ingest_company(
    session: AsyncSession,
    ticker: str,
    embedder: Embedder,
    max_transcripts: int = 10,
) -> dict:
    """
    Full ingestion pipeline for a company via SEC EDGAR.

    Searches EDGAR for the company, finds transcript filings,
    downloads and parses them, generates embeddings, and stores
    everything in the database.

    Args:
        session: Async database session
        ticker: Stock ticker symbol
        embedder: Initialized Embedder instance
        max_transcripts: Maximum number of transcripts to ingest

    Returns:
        Summary dict with counts of transcripts and chunks processed
    """
    summary = {
        "ticker": ticker,
        "transcripts_found": 0,
        "transcripts_ingested": 0,
        "chunks_created": 0,
        "errors": [],
    }

    async with EdgarClient() as client:
        # Step 1: Find the company
        companies = await client.search_company(ticker)
        if not companies:
            summary["errors"].append(f"Company not found for ticker: {ticker}")
            return summary

        edgar_company = companies[0]
        logger.info("Found company: %s (CIK: %s)", edgar_company.name, edgar_company.cik)

        # Create or get the company in our database
        company = await get_or_create_company(
            session,
            ticker=edgar_company.ticker,
            name=edgar_company.name,
            cik=edgar_company.cik,
        )
        company.ingestion_status = IngestionStatus.IN_PROGRESS

        # Step 2: Find transcript filings
        transcript_filings = await client.find_transcript_filings(
            cik=edgar_company.cik,
            max_results=max_transcripts,
        )
        summary["transcripts_found"] = len(transcript_filings)

        if not transcript_filings:
            # Try getting 8-K filings directly as fallback
            filings = await client.get_company_filings(
                cik=edgar_company.cik,
                form_types=["8-K", "6-K"],
            )
            logger.info("No EFTS results; found %d 8-K/6-K filings", len(filings))
            summary["errors"].append(
                "No transcript filings found via full-text search. "
                "The company may not file transcripts on EDGAR."
            )

        # Step 3: Process each filing
        for filing in transcript_filings[:max_transcripts]:
            try:
                # Download the filing
                if not filing.file_url:
                    continue

                html_content = await client.download_filing(filing.file_url)
                if not html_content or len(html_content) < 500:
                    continue

                # Parse the transcript
                parsed = parse_transcript(
                    html_content=html_content,
                    company_name=edgar_company.name,
                )

                if not parsed.turns:
                    logger.warning("No speaker turns found in filing: %s", filing.file_url)
                    continue

                # Check for duplicate (same company, quarter, year)
                existing = await session.execute(
                    select(Transcript).where(
                        Transcript.company_id == company.id,
                        Transcript.quarter == parsed.quarter,
                        Transcript.year == parsed.year,
                    )
                )
                if existing.scalar_one_or_none():
                    logger.info("Skipping duplicate: %s %s %d", ticker, parsed.quarter, parsed.year)
                    continue

                # Chunk the transcript
                chunks = chunk_transcript(parsed, ticker=ticker)
                if not chunks:
                    continue

                # Generate embeddings
                texts = [c.content for c in chunks]
                embeddings = embedder.embed_texts(texts)

                # Store in database
                await _store_transcript_chunks(
                    session=session,
                    company=company,
                    parsed=parsed,
                    chunks=chunks,
                    embeddings=embeddings,
                    filing_url=filing.file_url,
                    filing_date=filing.filing_date,
                    filing_type=filing.form_type,
                )

                summary["transcripts_ingested"] += 1
                summary["chunks_created"] += len(chunks)

            except Exception as exc:
                error_msg = f"Error processing filing {filing.file_url}: {exc}"
                logger.error(error_msg)
                summary["errors"].append(error_msg)
                continue

        # Update company status
        company.ingestion_status = (
            IngestionStatus.COMPLETED
            if summary["transcripts_ingested"] > 0
            else IngestionStatus.FAILED
        )

    return summary


async def ingest_from_json(
    session: AsyncSession,
    json_path: str | Path,
    embedder: Embedder,
) -> dict:
    """
    Ingest transcript data from a pre-structured JSON file.

    Used for seeding the database with sample data. The JSON
    file should contain a list of transcript objects matching
    the format expected by parse_transcript_from_json().

    Args:
        session: Async database session
        json_path: Path to the JSON file
        embedder: Initialized Embedder instance

    Returns:
        Summary dict with ingestion results
    """
    json_path = Path(json_path)
    logger.info("Loading transcripts from %s", json_path)

    with open(json_path, "r") as f:
        data = json.load(f)

    transcripts_data = data if isinstance(data, list) else [data]

    summary = {
        "file": str(json_path),
        "transcripts_ingested": 0,
        "chunks_created": 0,
        "errors": [],
    }

    for transcript_data in transcripts_data:
        try:
            ticker = transcript_data.get("ticker", "")
            company_name = transcript_data.get("company_name", "")

            # Get or create company
            company = await get_or_create_company(
                session,
                ticker=ticker,
                name=company_name,
                cik=transcript_data.get("cik", ""),
                sector=transcript_data.get("sector", ""),
                exchange=transcript_data.get("exchange", ""),
                is_sp500=transcript_data.get("is_sp500", False),
            )

            # Parse the transcript data
            parsed = parse_transcript_from_json(transcript_data)

            # Check for duplicate
            existing = await session.execute(
                select(Transcript).where(
                    Transcript.company_id == company.id,
                    Transcript.quarter == parsed.quarter,
                    Transcript.year == parsed.year,
                )
            )
            if existing.scalar_one_or_none():
                logger.info("Skipping duplicate: %s %s %d", ticker, parsed.quarter, parsed.year)
                continue

            # Chunk the transcript
            chunks = chunk_transcript(parsed, ticker=ticker)
            if not chunks:
                continue

            # Generate embeddings
            texts = [c.content for c in chunks]
            embeddings = embedder.embed_texts(texts, show_progress=True)

            # Store in database
            await _store_transcript_chunks(
                session=session,
                company=company,
                parsed=parsed,
                chunks=chunks,
                embeddings=embeddings,
            )

            company.ingestion_status = IngestionStatus.COMPLETED
            summary["transcripts_ingested"] += 1
            summary["chunks_created"] += len(chunks)

        except Exception as exc:
            error_msg = f"Error processing transcript: {exc}"
            logger.error(error_msg)
            summary["errors"].append(error_msg)

    return summary


async def ingest_seed_directory(
    session: AsyncSession,
    directory: str | Path,
    embedder: Embedder,
) -> dict:
    """
    Ingest all JSON transcript files from a directory.

    Scans the directory for .json files and processes each one.
    Used to bulk-load the initial dataset.

    Args:
        session: Async database session
        directory: Path to directory containing JSON transcript files
        embedder: Initialized Embedder instance

    Returns:
        Combined summary dict
    """
    directory = Path(directory)
    json_files = sorted(directory.glob("*.json"))
    logger.info("Found %d JSON files in %s", len(json_files), directory)

    total_summary = {
        "files_processed": 0,
        "transcripts_ingested": 0,
        "chunks_created": 0,
        "errors": [],
    }

    for json_file in json_files:
        result = await ingest_from_json(session, json_file, embedder)
        total_summary["files_processed"] += 1
        total_summary["transcripts_ingested"] += result["transcripts_ingested"]
        total_summary["chunks_created"] += result["chunks_created"]
        total_summary["errors"].extend(result["errors"])

    logger.info(
        "Seed complete: %d files, %d transcripts, %d chunks",
        total_summary["files_processed"],
        total_summary["transcripts_ingested"],
        total_summary["chunks_created"],
    )

    return total_summary
