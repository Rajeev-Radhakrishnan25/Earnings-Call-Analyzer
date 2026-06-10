"""
Multi-quarter sentiment analysis.

Coordinates the retrieval and LLM-based analysis of management
sentiment across multiple quarters for a single company. This
is the feature behind the resume claim: "LLM-powered multi-quarter
sentiment analysis."

The flow:
    1. Retrieve executive-spoken chunks across all available quarters
    2. Pass them to Claude for sentiment scoring
    3. Return structured scores with trend analysis
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.embedding.embedder import Embedder
from src.generation.generator import AnswerGenerator
from src.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)


async def analyze_sentiment(
    session: AsyncSession,
    ticker: str,
    company_name: str,
    embedder: Embedder,
    generator: AnswerGenerator,
    years: list[int] | None = None,
) -> dict:
    """
    Run multi-quarter sentiment analysis for a company.

    Retrieves executive remarks across all quarters and asks Claude
    to score the sentiment of each quarter on a -1.0 to +1.0 scale.

    Args:
        session: Database session
        ticker: Company ticker
        company_name: Company name for display
        embedder: Embedder instance
        generator: AnswerGenerator instance
        years: Optional year filter

    Returns:
        Dict with quarterly scores, labels, and trend analysis
    """
    retriever = HybridRetriever(embedder)

    # Use a broad query to capture overall management tone
    query = "company performance outlook strategy revenue growth guidance"

    result = await retriever.retrieve_temporal(
        session=session,
        query=query,
        company_tickers=[ticker],
        top_k_per_quarter=5,
        years=years,
    )

    if not result.chunks:
        return {
            "company": company_name,
            "ticker": ticker,
            "data_points": [],
            "overall_trend": "no_data",
            "analysis": f"No transcript data found for {ticker}.",
        }

    # Filter to executive speakers only (CEO, CFO, COO, CTO, executives)
    executive_roles = {"ceo", "cfo", "coo", "cto", "executive"}
    exec_chunks = [
        c for c in result.chunks
        if c.speaker_role in executive_roles
    ]

    # Fall back to all chunks if no executive chunks found
    if not exec_chunks:
        exec_chunks = result.chunks

    sentiment_data = generator.generate_sentiment_analysis(
        chunks=exec_chunks,
        company_name=company_name,
        ticker=ticker,
    )

    return {
        "company": company_name,
        "ticker": ticker,
        "data_points": sentiment_data.get("quarters", []),
        "overall_trend": sentiment_data.get("overall_trend", "unknown"),
        "analysis": sentiment_data.get("analysis", ""),
    }
