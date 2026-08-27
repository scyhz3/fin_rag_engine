"""Convert document chunks into embedding vectors."""

from dataclasses import dataclass
from typing import Protocol

from finrag.processing.chunker import DocumentChunk


class EmbeddingClient(Protocol):
    """Define the model operations required by the embedding pipeline."""

    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""
        ...


@dataclass(frozen=True)
class EmbeddedChunk:
    """Store a source chunk with its model-specific vector."""

    chunk: DocumentChunk
    vector: tuple[float, ...]
    embedding_model: str
    embedding_dimension: int


def embed_chunks(
    chunks: list[DocumentChunk],
    client: EmbeddingClient,
    batch_size: int = 100,
) -> list[EmbeddedChunk]:
    """Generate vectors for chunks in bounded batches.

    Args:
        chunks: Document chunks to convert into vectors.
        client: Embedding model client used for conversion.
        batch_size: Maximum number of texts sent in one request.

    Returns:
        Embedded chunks in the same order as the input chunks.

    Raises:
        ValueError: If settings or returned vectors are invalid.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    embedded = []
    expected_dimension = None
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = client.embed([chunk.text for chunk in batch])
        if len(vectors) != len(batch):
            raise ValueError("embedding client must return one vector per text")

        for chunk, vector in zip(batch, vectors):
            normalized = tuple(float(value) for value in vector)
            if not normalized:
                raise ValueError("embedding vectors must not be empty")
            if expected_dimension is None:
                expected_dimension = len(normalized)
            if len(normalized) != expected_dimension:
                raise ValueError("all embedding vectors must have the same dimension")

            embedded.append(
                EmbeddedChunk(
                    chunk=chunk,
                    vector=normalized,
                    embedding_model=client.model_name,
                    embedding_dimension=len(normalized),
                )
            )
    return embedded
