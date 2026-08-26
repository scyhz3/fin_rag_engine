"""Define vector storage types used by the retrieval pipeline."""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Protocol

from finrag.processing.chunker import DocumentChunk
from finrag.processing.embedding import EmbeddedChunk


@dataclass(frozen=True)
class SearchFilters:
    """Limit vector search to one report scope."""

    edinet_code: Optional[str] = None
    period_end: Optional[date] = None
    document_type: Optional[str] = None


@dataclass(frozen=True)
class SearchResult:
    """Store one retrieved chunk and its similarity score."""

    score: float
    chunk: DocumentChunk


class VectorStore(Protocol):
    """Define persistence operations required by retrieval."""

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        """Insert new chunks or replace chunks with the same ID."""
        ...

    def search(
        self,
        query_vector: list[float],
        filters: Optional[SearchFilters] = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Return the closest chunks after applying optional filters."""
        ...

    def close(self) -> None:
        """Close the underlying storage resources."""
        ...
