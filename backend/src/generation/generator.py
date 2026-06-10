"""
Answer generation using Claude Opus 4.6.

Takes retrieved chunks from the hybrid retriever and generates
cited answers, temporal comparisons, or sentiment analyses
by calling the Anthropic API.
"""

import json
import logging
import time

import anthropic

from src.config import get_settings
from src.generation.prompts import (
    SYSTEM_PROMPT,
    build_query_prompt,
    build_sentiment_prompt,
    build_temporal_prompt,
)
from src.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)
settings = get_settings()


def _chunks_to_dicts(chunks: list[RetrievedChunk]) -> list[dict]:
    """Convert RetrievedChunk objects to dicts for prompt templates."""
    return [
        {
            "content": c.content,
            "company_name": c.company_name,
            "ticker": c.ticker,
            "quarter": c.quarter,
            "year": c.year,
            "speaker_name": c.speaker_name,
            "speaker_role": c.speaker_role,
            "section_type": c.section_type,
            "similarity_score": c.similarity_score,
        }
        for c in chunks
    ]


class AnswerGenerator:
    """
    Generates cited answers using Claude Opus 4.6.

    Usage:
        generator = AnswerGenerator()
        answer = await generator.generate_answer(question, retrieved_chunks)
    """

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            logger.warning(
                "No Anthropic API key configured. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _call_claude(self, user_prompt: str, max_tokens: int = 2000) -> str:
        """
        Make a synchronous call to the Claude API.

        Uses claude-opus-4-6 as specified in the project requirements.
        """
        start = time.time()

        try:
            response = self._client.messages.create(
                model="claude-opus-4-6",
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            elapsed_ms = int((time.time() - start) * 1000)
            logger.info("Claude API call: %dms, tokens used: %d", elapsed_ms, response.usage.output_tokens)

            return response.content[0].text

        except anthropic.APIError as exc:
            logger.error("Claude API error: %s", exc)
            raise

    def generate_answer(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """
        Generate a cited answer to a natural language question.

        Passes the retrieved chunks as context to Claude, which
        synthesizes an answer with citations in
        [Company, Quarter Year, Speaker] format.

        Args:
            question: The user's question
            chunks: Retrieved transcript chunks with metadata

        Returns:
            Generated answer string with citations
        """
        if not chunks:
            return (
                "I could not find any relevant transcript excerpts to answer "
                "this question. Try broadening your search filters or adding "
                "more companies to the dataset."
            )

        chunk_dicts = _chunks_to_dicts(chunks)
        prompt = build_query_prompt(question, chunk_dicts)
        return self._call_claude(prompt)

    def generate_temporal_comparison(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        company_tickers: list[str],
    ) -> str:
        """
        Generate a temporal comparison across quarters.

        Chunks should be pre-sorted chronologically by the retriever.
        The LLM identifies trends, shifts, and changes over time.

        Args:
            question: The comparison question
            chunks: Chronologically sorted chunks
            company_tickers: Companies being compared

        Returns:
            Temporal analysis with quarter-by-quarter breakdown
        """
        if not chunks:
            return "No transcript data found for the specified companies and time range."

        chunk_dicts = _chunks_to_dicts(chunks)
        prompt = build_temporal_prompt(question, chunk_dicts, company_tickers)
        return self._call_claude(prompt, max_tokens=3000)

    def generate_sentiment_analysis(
        self,
        chunks: list[RetrievedChunk],
        company_name: str,
        ticker: str,
    ) -> dict:
        """
        Generate multi-quarter sentiment analysis.

        Returns structured JSON with sentiment scores per quarter,
        trend labels, and an overall analysis.

        Args:
            chunks: Chunks spanning multiple quarters for one company
            company_name: Company name for context
            ticker: Stock ticker

        Returns:
            Dict with quarterly sentiment scores and trend analysis
        """
        if not chunks:
            return {
                "quarters": [],
                "overall_trend": "insufficient_data",
                "analysis": "No transcript data available for sentiment analysis.",
            }

        chunk_dicts = _chunks_to_dicts(chunks)
        prompt = build_sentiment_prompt(chunk_dicts, company_name, ticker)
        raw_response = self._call_claude(prompt, max_tokens=2000)

        # Parse JSON response from Claude
        try:
            # Strip markdown code fences if present
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse sentiment JSON, returning raw response")
            return {
                "quarters": [],
                "overall_trend": "parse_error",
                "analysis": raw_response,
            }
