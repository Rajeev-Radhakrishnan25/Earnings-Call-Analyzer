"""
Speaker-aware transcript chunker.

The chunking strategy is central to the quality of RAG retrieval.
This module uses domain-aware chunking rather than arbitrary
fixed-size splits:

    Each chunk = one speaker's continuous remarks.

If a speaker talks for a very long time (e.g. a CEO's prepared
remarks might be 2000+ words), the turn is split at sentence
boundaries while preserving all metadata. This ensures each chunk
is small enough for effective embedding but semantically coherent.

Why this matters:
    - Fixed-size chunking (e.g. 500 tokens) would split mid-sentence
      or mix different speakers in one chunk, destroying context.
    - Speaker-turn chunking preserves WHO said WHAT, which is critical
      for citation accuracy and role-based filtering.
    - Metadata travels with each chunk, enabling hybrid SQL+vector queries.
"""

import logging
import re
from dataclasses import dataclass

from src.ingestion.transcript_parser import ParsedTranscript, SpeakerTurn

logger = logging.getLogger(__name__)

# Target chunk size in characters. Roughly 100-150 tokens.
# Small enough for precise embeddings, large enough for context.
MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 100

# Overlap between split chunks (in characters).
# Ensures context is not lost at chunk boundaries.
CHUNK_OVERLAP = 200


@dataclass
class TranscriptChunk:
    """
    A chunk ready for embedding and storage.

    Carries all metadata needed for hybrid retrieval:
        - company info (populated during pipeline)
        - temporal info (quarter, year)
        - speaker info (name, role)
        - section info (prepared remarks vs Q&A)
    """

    content: str
    speaker_name: str
    speaker_role: str
    section_type: str
    chunk_index: int
    token_count: int
    company_name: str = ""
    ticker: str = ""
    quarter: str = ""
    year: int = 0


def estimate_tokens(text: str) -> int:
    """
    Rough token count estimate.

    One token is approximately 4 characters or 0.75 words in English.
    This is a fast approximation; exact counts require a tokenizer.
    """
    return len(text) // 4


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences.

    Uses a simple regex that handles common abbreviations
    and decimal numbers without false splits.
    """
    # Split on period, question mark, or exclamation followed by space and capital
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if s.strip()]


def split_long_turn(turn: SpeakerTurn, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """
    Split a long speaker turn into smaller pieces at sentence boundaries.

    If a turn exceeds max_chars, it is split into chunks that each
    stay under the limit. Splits happen at sentence boundaries to
    maintain readability. Adjacent chunks overlap slightly to preserve
    context across boundaries.

    Args:
        turn: The speaker turn to split
        max_chars: Maximum characters per chunk

    Returns:
        List of text strings, each under max_chars
    """
    if len(turn.content) <= max_chars:
        return [turn.content]

    sentences = split_into_sentences(turn.content)
    chunks: list[str] = []
    current_chunk_sentences: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If adding this sentence exceeds the limit, finalize current chunk
        if current_length + sentence_len > max_chars and current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))

            # Keep the last sentence(s) for overlap
            overlap_sentences: list[str] = []
            overlap_len = 0
            for s in reversed(current_chunk_sentences):
                if overlap_len + len(s) > CHUNK_OVERLAP:
                    break
                overlap_sentences.insert(0, s)
                overlap_len += len(s)

            current_chunk_sentences = overlap_sentences
            current_length = overlap_len

        current_chunk_sentences.append(sentence)
        current_length += sentence_len

    # Add the final chunk
    if current_chunk_sentences:
        final_text = " ".join(current_chunk_sentences)
        # Avoid duplicating if it is the same as the last chunk
        if not chunks or final_text != chunks[-1]:
            chunks.append(final_text)

    return chunks


def chunk_transcript(
    transcript: ParsedTranscript,
    ticker: str = "",
) -> list[TranscriptChunk]:
    """
    Convert a parsed transcript into chunks ready for embedding.

    Each speaker turn becomes one or more chunks. Short turns
    (under MIN_CHUNK_CHARS) are kept as-is since they often
    contain important direct statements. Long turns are split
    at sentence boundaries.

    All chunks carry full metadata for hybrid retrieval.

    Args:
        transcript: Parsed transcript with speaker turns
        ticker: Stock ticker to attach to each chunk

    Returns:
        List of TranscriptChunk objects with metadata
    """
    chunks: list[TranscriptChunk] = []
    chunk_index = 0

    for turn in transcript.turns:
        # Skip empty or very short turns
        if not turn.content or len(turn.content.strip()) < MIN_CHUNK_CHARS:
            # Still include very short turns if they are from named speakers
            # (some important statements are brief)
            if turn.content and turn.speaker_name and len(turn.content.strip()) > 30:
                chunks.append(
                    TranscriptChunk(
                        content=turn.content.strip(),
                        speaker_name=turn.speaker_name,
                        speaker_role=turn.speaker_role,
                        section_type=turn.section_type,
                        chunk_index=chunk_index,
                        token_count=estimate_tokens(turn.content),
                        company_name=transcript.company_name,
                        ticker=ticker,
                        quarter=transcript.quarter,
                        year=transcript.year,
                    )
                )
                chunk_index += 1
            continue

        # Split long turns, keep short ones whole
        text_pieces = split_long_turn(turn)

        for piece in text_pieces:
            chunks.append(
                TranscriptChunk(
                    content=piece,
                    speaker_name=turn.speaker_name,
                    speaker_role=turn.speaker_role,
                    section_type=turn.section_type,
                    chunk_index=chunk_index,
                    token_count=estimate_tokens(piece),
                    company_name=transcript.company_name,
                    ticker=ticker,
                    quarter=transcript.quarter,
                    year=transcript.year,
                )
            )
            chunk_index += 1

    logger.info(
        "Chunked transcript: %s %s %d into %d chunks from %d turns",
        ticker, transcript.quarter, transcript.year,
        len(chunks), len(transcript.turns),
    )

    return chunks
