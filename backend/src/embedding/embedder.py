"""
Embedding generation using sentence-transformers.

This module wraps the all-MiniLM-L6-v2 model, which produces
384-dimensional vectors from text. The model runs entirely
locally with no API calls and no cost.

Why all-MiniLM-L6-v2:
    - Free and open source
    - 384 dimensions (small, fast to index and search)
    - Good quality for semantic similarity tasks
    - Fast inference, even on CPU
    - Widely used and well-tested

The same model must be used for both indexing (embedding chunks)
and querying (embedding the user's question). Using different
models would produce incompatible vector spaces.
"""

import logging
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _load_model():  # type: ignore[no-untyped-def]
    """
    Load the sentence-transformer model.

    Cached so it is loaded once and reused across all requests.
    First load downloads the model (~80MB) if not already cached.
    Subsequent loads are instant from disk cache.
    """
    from sentence_transformers import SentenceTransformer

    model_name = settings.embedding_model
    logger.info("Loading embedding model: %s", model_name)
    model = SentenceTransformer(model_name)
    logger.info(
        "Model loaded. Dimension: %d",
        model.get_sentence_embedding_dimension(),
    )
    return model


class Embedder:
    """
    Generates text embeddings using sentence-transformers.

    Usage:
        embedder = Embedder()
        vectors = embedder.embed_texts(["Hello world", "Earnings grew 15%"])
        query_vector = embedder.embed_query("What was the revenue growth?")
    """

    def __init__(self) -> None:
        self._model = _load_model()

    @property
    def dimension(self) -> int:
        """Return the embedding dimension (384 for all-MiniLM-L6-v2)."""
        return int(self._model.get_sentence_embedding_dimension())

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = 64,
        show_progress: bool = False,
    ) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Used during ingestion to embed all chunks from a transcript.
        Processes texts in batches for memory efficiency.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once
            show_progress: Show a progress bar (useful for large batches)

        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not texts:
            return []

        logger.debug("Embedding %d texts (batch_size=%d)", len(texts), batch_size)

        embeddings: NDArray[np.float32] = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )

        # Convert numpy array to list of lists for database storage
        return embeddings.tolist()  # type: ignore[no-any-return]

    def embed_query(self, query: str) -> list[float]:
        """
        Generate an embedding for a single query string.

        Used at query time to convert the user's question into
        a vector for similarity search against stored chunk embeddings.

        The embedding is L2-normalized (unit length) so cosine
        similarity can be computed as a simple dot product.

        Args:
            query: The user's natural language question

        Returns:
            A single embedding vector (list of floats)
        """
        embedding: NDArray[np.float32] = self._model.encode(
            query,
            normalize_embeddings=True,
        )
        return embedding.tolist()  # type: ignore[no-any-return]
