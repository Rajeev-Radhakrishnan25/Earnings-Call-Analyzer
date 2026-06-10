"""
Temporal comparison engine.

Handles questions like "How has Microsoft's cloud revenue narrative
changed over the past year?" by:
    1. Using temporal retrieval to get relevant chunks per quarter
    2. Passing them chronologically to Claude for synthesis
    3. Returning a structured comparison with citations

This module supports both single-company trends and cross-company
comparisons over time.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.embedding.embedder import Embedder
from src.generation.generator import AnswerGenerator
from src.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)


async def compare_temporal(
    session: AsyncSession,
    question: str,
    company_tickers: list[str],
    embedder: Embedder,
    generator: AnswerGenerator,
    years: list[int] | None = None,
    quarters: list[str] | None = None,
    top_k_per_quarter: int = 3,
) -> dict:
    """
    Perform temporal comparison across quarters.

    Retrieves relevant chunks per quarter (ensuring every quarter
    is represented) and generates a chronological analysis.

    Args:
        session: Database session
        question: The temporal comparison question
        company_tickers: Companies to analyze
        embedder: Embedder instance
        generator: AnswerGenerator instance
        years: Optional year filter
        quarters: Optional quarter filter
        top_k_per_quarter: Chunks per quarter to retrieve

    Returns:
        Dict with the generated comparison, citations, and metadata
    """
    retriever = HybridRetriever(embedder)

    result = await retriever.retrieve_temporal(
        session=session,
        query=question,
        company_tickers=company_tickers,
        top_k_per_quarter=top_k_per_quarter,
        years=years,
        quarters=quarters,
    )

    if not result.chunks:
        return {
            "answer": (
                "No transcript data found for the specified companies "
                "and time range. Try adding more companies or broadening "
                "the date range."
            ),
            "quarters_analyzed": 0,
            "companies": company_tickers,
            "retrieval_time_ms": result.retrieval_time_ms,
        }

    # Count distinct quarters in results
    quarter_set = {(c.quarter, c.year) for c in result.chunks}

    answer = generator.generate_temporal_comparison(
        question=question,
        chunks=result.chunks,
        company_tickers=company_tickers,
    )

    # Build citation list
    citations = []
    for chunk in result.chunks:
        citations.append({
            "company": chunk.company_name,
            "ticker": chunk.ticker,
            "quarter": chunk.quarter,
            "year": chunk.year,
            "speaker": chunk.speaker_name,
            "speaker_role": chunk.speaker_role,
            "section": chunk.section_type,
            "excerpt": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            "relevance_score": chunk.similarity_score,
        })

    return {
        "answer": answer,
        "citations": citations,
        "quarters_analyzed": len(quarter_set),
        "companies": result.companies_searched,
        "retrieval_time_ms": result.retrieval_time_ms,
    }
