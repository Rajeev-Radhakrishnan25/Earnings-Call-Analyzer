"""
Prompt templates for Claude Opus 4.6 integration.

These prompts are structured to produce accurate, cited answers
from earnings call transcript data. Key design decisions:

    1. System prompt establishes the role and citation format
    2. Context is presented with clear metadata headers per chunk
    3. The instruction explicitly requires citations and prohibits
       information not found in the provided context (anti-hallucination)
    4. Temporal and sentiment prompts have specialized structures
"""

SYSTEM_PROMPT = """You are a financial analyst assistant that answers questions \
about earnings call transcripts. You provide accurate, well-cited answers \
based strictly on the transcript excerpts provided to you.

Rules you must follow:
- Only use information from the provided transcript excerpts
- Cite every claim using [Company, Quarter Year, Speaker] format
- If the provided excerpts do not contain enough information to answer, say so clearly
- Never fabricate quotes or financial figures not present in the excerpts
- When comparing across quarters, organize your answer chronologically
- Use precise financial language appropriate for an analyst audience
- Keep answers concise and structured"""


def build_query_prompt(
    question: str,
    chunks: list[dict],
) -> str:
    """
    Build a prompt for answering a natural language query.

    The chunks are formatted with clear metadata headers so the
    LLM can attribute information to specific speakers, quarters,
    and companies.

    Args:
        question: The user's natural language question
        chunks: List of chunk dicts with content and metadata

    Returns:
        Formatted prompt string for the messages API
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Excerpt {i}]\n"
            f"Company: {chunk['company_name']} ({chunk['ticker']})\n"
            f"Quarter: {chunk['quarter']} {chunk['year']}\n"
            f"Speaker: {chunk['speaker_name']} ({chunk['speaker_role']})\n"
            f"Section: {chunk['section_type']}\n"
            f"Content: {chunk['content']}\n"
        )

    context_block = "\n---\n".join(context_parts)

    return (
        f"Based on the following earnings call transcript excerpts, "
        f"answer this question:\n\n"
        f"Question: {question}\n\n"
        f"Transcript Excerpts:\n\n{context_block}\n\n"
        f"Provide a clear, well-structured answer with citations in "
        f"[Company, Quarter Year, Speaker] format for each claim. "
        f"If the excerpts do not contain sufficient information to "
        f"fully answer the question, state what is missing."
    )


def build_temporal_prompt(
    question: str,
    chunks: list[dict],
    company_tickers: list[str],
) -> str:
    """
    Build a prompt for temporal comparison across quarters.

    Chunks are grouped by quarter and presented chronologically,
    making it easy for the LLM to identify trends and shifts.

    Args:
        question: The user's question about trends/changes
        chunks: Chronologically sorted chunk dicts
        company_tickers: Companies being compared

    Returns:
        Formatted prompt string
    """
    # Group chunks by quarter
    quarters: dict[str, list[dict]] = {}
    for chunk in chunks:
        key = f"{chunk['quarter']} {chunk['year']}"
        if key not in quarters:
            quarters[key] = []
        quarters[key].append(chunk)

    context_parts = []
    for quarter_label, quarter_chunks in quarters.items():
        excerpts = []
        for chunk in quarter_chunks:
            excerpts.append(
                f"  Speaker: {chunk['speaker_name']} ({chunk['speaker_role']})\n"
                f"  Section: {chunk['section_type']}\n"
                f"  Content: {chunk['content']}"
            )
        context_parts.append(
            f"=== {quarter_label} ===\n" + "\n\n".join(excerpts)
        )

    context_block = "\n\n".join(context_parts)
    companies_str = ", ".join(company_tickers)

    return (
        f"Analyze the following earnings call excerpts from {companies_str} "
        f"across multiple quarters to answer this question:\n\n"
        f"Question: {question}\n\n"
        f"Excerpts (organized chronologically):\n\n{context_block}\n\n"
        f"In your answer:\n"
        f"1. Identify the key narrative or metric being tracked\n"
        f"2. Describe how it has changed quarter over quarter\n"
        f"3. Note any significant shifts in tone, strategy, or outlook\n"
        f"4. Cite each observation with [Company, Quarter Year, Speaker]\n"
        f"5. Conclude with an overall trend assessment"
    )


def build_sentiment_prompt(
    chunks: list[dict],
    company_name: str,
    ticker: str,
) -> str:
    """
    Build a prompt for sentiment analysis across quarters.

    Asks the LLM to score management sentiment on a scale from
    -1.0 (very negative) to +1.0 (very positive) for each quarter,
    with justification.

    Args:
        chunks: Chunks grouped by quarter, sorted chronologically
        company_name: Full company name
        ticker: Stock ticker

    Returns:
        Formatted prompt string
    """
    quarters: dict[str, list[dict]] = {}
    for chunk in chunks:
        key = f"{chunk['quarter']} {chunk['year']}"
        if key not in quarters:
            quarters[key] = []
        quarters[key].append(chunk)

    context_parts = []
    for quarter_label, quarter_chunks in quarters.items():
        combined_text = " ".join(c["content"] for c in quarter_chunks)
        # Truncate to keep prompt manageable
        if len(combined_text) > 3000:
            combined_text = combined_text[:3000] + "..."
        context_parts.append(f"=== {quarter_label} ===\n{combined_text}")

    context_block = "\n\n".join(context_parts)

    return (
        f"Analyze the management sentiment in these earnings call excerpts "
        f"from {company_name} ({ticker}).\n\n"
        f"Excerpts by quarter:\n\n{context_block}\n\n"
        f"For each quarter, provide:\n"
        f"1. A sentiment score from -1.0 (very negative/pessimistic) to "
        f"+1.0 (very positive/bullish), with 0.0 being neutral\n"
        f"2. A one-word label: bullish, positive, neutral, cautious, or bearish\n"
        f"3. A brief summary (1-2 sentences) explaining the score\n\n"
        f"Then provide an overall trend assessment.\n\n"
        f"Respond in this exact JSON format:\n"
        f'{{\n'
        f'  "quarters": [\n'
        f'    {{"quarter": "Q1", "year": 2024, "score": 0.6, '
        f'"label": "positive", "summary": "..."}}\n'
        f'  ],\n'
        f'  "overall_trend": "...",\n'
        f'  "analysis": "..."\n'
        f'}}\n\n'
        f"Return ONLY valid JSON with no additional text."
    )
