"""
Hybrid retrieval engine combining vector similarity with metadata filtering.

This is the core of the RAG pipeline. It uses pgvector's cosine distance
operator alongside standard SQL WHERE clauses in a single query:

    SELECT chunks.*, 1 - (embedding <=> :query_vector) AS similarity
    FROM chunks
    JOIN transcripts ON ...
    JOIN companies ON ...
    WHERE companies.ticker IN ('AAPL', 'MSFT')
      AND transcripts.year >= 2024
      AND chunks.section_type = 'qa'
    ORDER BY embedding <=> :query_vector
    LIMIT 10

The <=> operator computes cosine distance. Since our embeddings are
L2-normalized, cosine distance = 1 - cosine_similarity. Lower distance
means higher similarity.

This hybrid approach is the key advantage of pgvector over standalone
vector databases: you get SQL expressiveness for free. Pinecone or
Weaviate would require separate metadata filters; here it is just
a WHERE clause in the same query.
"""

import logging
import time
from dataclasses import dataclass, field

from sqlalchemy import select, and_, or_, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Chunk, Company, SectionType, SpeakerRole, Transcript
from src.embedding.embedder import Embedder

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A chunk returned by the retriever with all context needed for generation."""

    chunk_id: int
    content: str
    speaker_name: str
    speaker_role: str
    section_type: str
    company_name: str
    ticker: str
    quarter: str
    year: int
    similarity_score: float
    chunk_index: int = 0
    sentiment_score: float | None = None


@dataclass
class RetrievalResult:
    """Complete retrieval result with timing and metadata."""

    chunks: list[RetrievedChunk]
    query_text: str
    retrieval_time_ms: int
    total_chunks_searched: int
    companies_searched: list[str] = field(default_factory=list)


class HybridRetriever:
    """
    Retrieves relevant transcript chunks using hybrid vector + metadata search.

    Supports filtering by:
        - Company tickers (e.g. ["AAPL", "MSFT"])
        - Year range (e.g. [2024, 2025])
        - Quarters (e.g. ["Q1", "Q3"])
        - Section type (prepared_remarks or qa)
        - Speaker roles (e.g. ["ceo", "cfo"])

    All filters are optional. When no filters are applied, the search
    runs across the entire dataset.
    """

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        top_k: int = 10,
        company_tickers: list[str] | None = None,
        years: list[int] | None = None,
        quarters: list[str] | None = None,
        section_type: str | None = None,
        speaker_roles: list[str] | None = None,
    ) -> RetrievalResult:
        """
        Perform hybrid retrieval: vector similarity + metadata filtering.

        Args:
            session: Async database session
            query: Natural language query to search for
            top_k: Number of top results to return
            company_tickers: Filter by company tickers
            years: Filter by fiscal years
            quarters: Filter by quarters (Q1, Q2, Q3, Q4)
            section_type: Filter by section (prepared_remarks, qa)
            speaker_roles: Filter by speaker roles (ceo, cfo, analyst)

        Returns:
            RetrievalResult with ranked chunks and metadata
        """
        start_time = time.time()

        # Step 1: Embed the query
        query_embedding = self._embedder.embed_query(query)

        # Step 2: Build the hybrid query
        # The cosine distance operator <=> returns distance (lower = more similar)
        # We compute similarity as 1 - distance
        cosine_distance = Chunk.embedding.cosine_distance(query_embedding)

        stmt = (
            select(
                Chunk,
                Company.name.label("company_name"),
                Company.ticker.label("ticker"),
                Transcript.quarter.label("quarter"),
                Transcript.year.label("year"),
                (1 - cosine_distance).label("similarity"),
            )
            .join(Transcript, Chunk.transcript_id == Transcript.id)
            .join(Company, Transcript.company_id == Company.id)
        )

        # Step 3: Apply metadata filters
        conditions = []

        if company_tickers:
            upper_tickers = [t.upper() for t in company_tickers]
            conditions.append(Company.ticker.in_(upper_tickers))

        if years:
            conditions.append(Transcript.year.in_(years))

        if quarters:
            upper_quarters = [q.upper() for q in quarters]
            conditions.append(Transcript.quarter.in_(upper_quarters))

        if section_type:
            try:
                section_enum = SectionType(section_type)
                conditions.append(Chunk.section_type == section_enum)
            except ValueError:
                logger.warning("Invalid section_type filter: %s", section_type)

        if speaker_roles:
            role_enums = []
            for role in speaker_roles:
                try:
                    role_enums.append(SpeakerRole(role))
                except ValueError:
                    logger.warning("Invalid speaker_role filter: %s", role)
            if role_enums:
                conditions.append(Chunk.speaker_role.in_(role_enums))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Step 4: Order by similarity and limit
        stmt = stmt.order_by(cosine_distance).limit(top_k)

        # Step 5: Execute
        result = await session.execute(stmt)
        rows = result.all()

        # Step 6: Build response
        chunks = []
        companies_found: set[str] = set()

        for row in rows:
            chunk = row[0]
            company_name = row[1]
            ticker = row[2]
            quarter = row[3]
            year = row[4]
            similarity = float(row[5]) if row[5] is not None else 0.0

            companies_found.add(ticker)

            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    speaker_name=chunk.speaker_name or "Unknown",
                    speaker_role=chunk.speaker_role.value if chunk.speaker_role else "unknown",
                    section_type=chunk.section_type.value if chunk.section_type else "unknown",
                    company_name=company_name,
                    ticker=ticker,
                    quarter=quarter,
                    year=year,
                    similarity_score=similarity,
                    chunk_index=chunk.chunk_index,
                    sentiment_score=chunk.sentiment_score,
                )
            )

        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Retrieved %d chunks in %dms for query: '%s' (filters: tickers=%s, years=%s)",
            len(chunks), elapsed_ms, query[:80], company_tickers, years,
        )

        return RetrievalResult(
            chunks=chunks,
            query_text=query,
            retrieval_time_ms=elapsed_ms,
            total_chunks_searched=0,
            companies_searched=sorted(companies_found),
        )

    async def retrieve_temporal(
        self,
        session: AsyncSession,
        query: str,
        company_tickers: list[str],
        top_k_per_quarter: int = 3,
        years: list[int] | None = None,
        quarters: list[str] | None = None,
    ) -> RetrievalResult:
        """
        Temporal retrieval: get relevant chunks per quarter for comparison.

        Instead of a single ranked list, this retrieves the top-K most
        relevant chunks FOR EACH quarter. This ensures every quarter
        is represented in the results, enabling temporal comparison
        even if one quarter dominates in pure similarity ranking.

        Args:
            session: Async database session
            query: Natural language query
            company_tickers: Companies to compare across time
            top_k_per_quarter: Chunks to retrieve per quarter
            years: Optional year filter
            quarters: Optional quarter filter

        Returns:
            RetrievalResult with chunks organized for temporal comparison
        """
        start_time = time.time()
        query_embedding = self._embedder.embed_query(query)

        # Determine which quarters exist for these companies
        quarter_stmt = (
            select(
                Transcript.quarter,
                Transcript.year,
            )
            .join(Company, Transcript.company_id == Company.id)
            .where(Company.ticker.in_([t.upper() for t in company_tickers]))
            .distinct()
            .order_by(Transcript.year, Transcript.quarter)
        )

        if years:
            quarter_stmt = quarter_stmt.where(Transcript.year.in_(years))
        if quarters:
            quarter_stmt = quarter_stmt.where(Transcript.quarter.in_([q.upper() for q in quarters]))

        quarter_result = await session.execute(quarter_stmt)
        available_quarters = [(row[0], row[1]) for row in quarter_result.all()]

        # Retrieve top chunks for each quarter
        all_chunks: list[RetrievedChunk] = []
        companies_found: set[str] = set()

        cosine_distance = Chunk.embedding.cosine_distance(query_embedding)

        for q, y in available_quarters:
            stmt = (
                select(
                    Chunk,
                    Company.name.label("company_name"),
                    Company.ticker.label("ticker"),
                    Transcript.quarter.label("quarter"),
                    Transcript.year.label("year"),
                    (1 - cosine_distance).label("similarity"),
                )
                .join(Transcript, Chunk.transcript_id == Transcript.id)
                .join(Company, Transcript.company_id == Company.id)
                .where(
                    and_(
                        Company.ticker.in_([t.upper() for t in company_tickers]),
                        Transcript.quarter == q,
                        Transcript.year == y,
                    )
                )
                .order_by(cosine_distance)
                .limit(top_k_per_quarter)
            )

            result = await session.execute(stmt)
            for row in result.all():
                chunk = row[0]
                companies_found.add(row[2])
                all_chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk.id,
                        content=chunk.content,
                        speaker_name=chunk.speaker_name or "Unknown",
                        speaker_role=chunk.speaker_role.value if chunk.speaker_role else "unknown",
                        section_type=chunk.section_type.value if chunk.section_type else "unknown",
                        company_name=row[1],
                        ticker=row[2],
                        quarter=row[3],
                        year=row[4],
                        similarity_score=float(row[5]) if row[5] is not None else 0.0,
                        chunk_index=chunk.chunk_index,
                        sentiment_score=chunk.sentiment_score,
                    )
                )

        # Sort chronologically for temporal analysis
        all_chunks.sort(key=lambda c: (c.year, c.quarter))

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Temporal retrieval: %d chunks across %d quarters in %dms",
            len(all_chunks), len(available_quarters), elapsed_ms,
        )

        return RetrievalResult(
            chunks=all_chunks,
            query_text=query,
            retrieval_time_ms=elapsed_ms,
            total_chunks_searched=0,
            companies_searched=sorted(companies_found),
        )
