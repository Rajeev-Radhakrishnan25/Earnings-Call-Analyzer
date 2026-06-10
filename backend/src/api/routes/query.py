"""
Query API routes.

The main endpoint where users submit natural language questions
and receive cited answers. Supports three modes:

    1. Standard query: Retrieve + generate with citations
    2. Temporal comparison: Multi-quarter trend analysis
    3. Sentiment analysis: Management tone over time

All modes use the same hybrid retrieval engine with optional
metadata filters.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.analysis.sentiment import analyze_sentiment
from src.analysis.temporal import compare_temporal
from src.api.schemas import (
    Citation,
    QueryRequest,
    QueryResponse,
    SentimentResponse,
    SentimentDataPoint,
)
from src.config import get_settings
from src.database.connection import get_db_session
from src.embedding.embedder import Embedder
from src.generation.generator import AnswerGenerator
from src.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


def get_embedder() -> Embedder:
    """Dependency that provides the shared Embedder instance."""
    return Embedder()


def get_generator() -> AnswerGenerator:
    """Dependency that provides the AnswerGenerator instance."""
    return AnswerGenerator()


@router.post("/query", response_model=QueryResponse)
async def query_transcripts(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db_session),
    embedder: Embedder = Depends(get_embedder),
    generator: AnswerGenerator = Depends(get_generator),
) -> QueryResponse:
    """
    Submit a natural language query against earnings call transcripts.

    Supports optional filters for company, quarter, year, section,
    and speaker role. Can optionally enable temporal comparison
    or sentiment analysis modes.
    """
    start_time = time.time()

    try:
        retriever = HybridRetriever(embedder)

        if request.enable_temporal_comparison and request.company_tickers:
            # Temporal comparison mode
            result = await compare_temporal(
                session=session,
                question=request.question,
                company_tickers=request.company_tickers,
                embedder=embedder,
                generator=generator,
                years=request.years,
                quarters=request.quarters,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            return QueryResponse(
                answer=result["answer"],
                citations=[
                    Citation(**c) for c in result.get("citations", [])
                ],
                query_time_ms=elapsed_ms,
                chunks_retrieved=len(result.get("citations", [])),
                companies_searched=result.get("companies", []),
            )

        else:
            # Standard query mode
            retrieval_result = await retriever.retrieve(
                session=session,
                query=request.question,
                top_k=request.top_k,
                company_tickers=request.company_tickers,
                years=request.years,
                quarters=request.quarters,
                section_type=request.section_type,
                speaker_roles=request.speaker_roles,
            )

            # Generate answer with citations
            answer = generator.generate_answer(
                question=request.question,
                chunks=retrieval_result.chunks,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            citations = [
                Citation(
                    company=chunk.company_name,
                    ticker=chunk.ticker,
                    quarter=chunk.quarter,
                    year=chunk.year,
                    speaker=chunk.speaker_name,
                    speaker_role=chunk.speaker_role,
                    section=chunk.section_type,
                    excerpt=(
                        chunk.content[:200] + "..."
                        if len(chunk.content) > 200
                        else chunk.content
                    ),
                    relevance_score=chunk.similarity_score,
                )
                for chunk in retrieval_result.chunks
            ]

            return QueryResponse(
                answer=answer,
                citations=citations,
                query_time_ms=elapsed_ms,
                chunks_retrieved=len(retrieval_result.chunks),
                companies_searched=retrieval_result.companies_searched,
            )

    except Exception as exc:
        logger.error("Query failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(exc)}",
        )


@router.post("/query/sentiment", response_model=SentimentResponse)
async def query_sentiment(
    ticker: str,
    session: AsyncSession = Depends(get_db_session),
    embedder: Embedder = Depends(get_embedder),
    generator: AnswerGenerator = Depends(get_generator),
) -> SentimentResponse:
    """
    Run multi-quarter sentiment analysis for a company.

    Returns sentiment scores (-1.0 to +1.0) per quarter with
    labels (bullish/positive/neutral/cautious/bearish) and
    an overall trend assessment.
    """
    from sqlalchemy import select
    from src.database.models import Company

    # Look up company
    result = await session.execute(
        select(Company).where(Company.ticker == ticker.upper())
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company {ticker} not found. Ingest it first.",
        )

    try:
        sentiment_result = await analyze_sentiment(
            session=session,
            ticker=company.ticker,
            company_name=company.name,
            embedder=embedder,
            generator=generator,
        )

        data_points = [
            SentimentDataPoint(
                quarter=dp.get("quarter", ""),
                year=dp.get("year", 0),
                score=dp.get("score", 0.0),
                label=dp.get("label", "unknown"),
                summary=dp.get("summary", ""),
            )
            for dp in sentiment_result.get("data_points", [])
        ]

        return SentimentResponse(
            company=company.name,
            ticker=company.ticker,
            data_points=data_points,
            overall_trend=sentiment_result.get("overall_trend", "unknown"),
            analysis=sentiment_result.get("analysis", ""),
        )

    except Exception as exc:
        logger.error("Sentiment analysis failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Sentiment analysis failed: {str(exc)}",
        )
