"""Persist and search embedded chunks with local Qdrant."""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from finrag.processing.chunker import DocumentChunk
from finrag.processing.embedding import EmbeddedChunk
from finrag.storage.vector_store import SearchFilters, SearchResult


DEFAULT_COLLECTION = "edinet_chunks"
DEFAULT_BATCH_SIZE = 100


class QdrantVectorStore:
    """Store EDINET chunks in an embedded Qdrant database."""

    def __init__(
        self,
        path: Path,
        collection_name: str = DEFAULT_COLLECTION,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        """Open a local Qdrant database.

        Args:
            path: Directory where Qdrant persists its files.
            collection_name: Collection used for EDINET chunks.
            batch_size: Maximum points written in one operation.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        self.collection_name = collection_name
        self.batch_size = batch_size
        self._client = QdrantClient(path=str(path))

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        """Insert or replace embedded chunks by stable chunk ID."""
        if not chunks:
            return

        dimension, model_name = self._validate_chunks(chunks)
        self._ensure_collection(dimension, model_name)

        for start in range(0, len(chunks), self.batch_size):
            batch = chunks[start : start + self.batch_size]
            self._client.upsert(
                collection_name=self.collection_name,
                points=[self._point(chunk) for chunk in batch],
            )

    def search(
        self,
        query_vector: list[float],
        filters: Optional[SearchFilters] = None,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Return chunks ordered by cosine similarity."""
        if not query_vector:
            raise ValueError("query_vector must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not self._client.collection_exists(self.collection_name):
            return []

        response = self._client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=self._build_filter(filters),
            limit=top_k,
            with_payload=True,
        )
        return [
            SearchResult(
                score=float(point.score),
                chunk=self._read_chunk(point.payload or {}),
            )
            for point in response.points
        ]

    def close(self) -> None:
        """Close the local Qdrant database."""
        self._client.close()

    def _ensure_collection(self, dimension: int, model_name: str) -> None:
        """Create the collection or validate its vector contract."""
        if not self._client.collection_exists(self.collection_name):
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                ),
            )
            return

        info = self._client.get_collection(self.collection_name)
        vectors_config = info.config.params.vectors
        stored_dimension = getattr(vectors_config, "size", None)
        if stored_dimension != dimension:
            raise ValueError("embedding dimension does not match the collection")

        records, _ = self._client.scroll(
            collection_name=self.collection_name,
            limit=1,
            with_payload=["embedding_model"],
            with_vectors=False,
        )
        if records:
            stored_model = (records[0].payload or {}).get("embedding_model")
            if stored_model != model_name:
                raise ValueError("embedding model does not match the collection")

    @staticmethod
    def _validate_chunks(chunks: list[EmbeddedChunk]) -> tuple[int, str]:
        """Return the shared vector dimension and model name."""
        dimension = chunks[0].embedding_dimension
        model_name = chunks[0].embedding_model
        for item in chunks:
            if len(item.vector) != item.embedding_dimension:
                raise ValueError("embedding dimension does not match vector length")
            if item.embedding_dimension != dimension:
                raise ValueError("all chunks must have the same embedding dimension")
            if item.embedding_model != model_name:
                raise ValueError("all chunks must use the same embedding model")
        return dimension, model_name

    @staticmethod
    def _point(item: EmbeddedChunk) -> models.PointStruct:
        """Convert an embedded chunk into a Qdrant point."""
        return models.PointStruct(
            id=str(uuid5(NAMESPACE_URL, f"finrag:{item.chunk.chunk_id}")),
            vector=list(item.vector),
            payload={
                "chunk_id": item.chunk.chunk_id,
                "company_name": item.chunk.company_name,
                "edinet_code": item.chunk.edinet_code,
                "doc_id": item.chunk.doc_id,
                "logical_report_id": item.chunk.logical_report_id,
                "document_type": item.chunk.document_type,
                "submitted_at": item.chunk.submitted_at.isoformat(),
                "period_start": item.chunk.period_start.isoformat(),
                "period_end": item.chunk.period_end.isoformat(),
                "is_correction": item.chunk.is_correction,
                "section_title": item.chunk.section_title,
                "section_level": item.chunk.section_level,
                "section_order": item.chunk.section_order,
                "heading_path": list(item.chunk.heading_path),
                "source_file": item.chunk.source_file,
                "chunk_index": item.chunk.chunk_index,
                "text": item.chunk.text,
                "embedding_model": item.embedding_model,
                "embedding_dimension": item.embedding_dimension,
            },
        )

    @staticmethod
    def _build_filter(
        filters: Optional[SearchFilters],
    ) -> Optional[models.Filter]:
        """Convert search filters into Qdrant field conditions."""
        if filters is None:
            return None

        values = {
            "edinet_code": filters.edinet_code,
            "period_end": (
                filters.period_end.isoformat() if filters.period_end else None
            ),
            "document_type": filters.document_type,
        }
        conditions = [
            models.FieldCondition(
                key=key,
                match=models.MatchValue(value=value),
            )
            for key, value in values.items()
            if value is not None
        ]
        return models.Filter(must=conditions) if conditions else None

    @staticmethod
    def _read_chunk(payload: dict[str, Any]) -> DocumentChunk:
        """Restore a document chunk from its Qdrant payload."""
        return DocumentChunk(
            chunk_id=str(payload["chunk_id"]),
            company_name=str(payload["company_name"]),
            edinet_code=str(payload["edinet_code"]),
            doc_id=str(payload["doc_id"]),
            logical_report_id=str(payload["logical_report_id"]),
            document_type=str(payload["document_type"]),
            submitted_at=datetime.fromisoformat(str(payload["submitted_at"])),
            period_start=date.fromisoformat(str(payload["period_start"])),
            period_end=date.fromisoformat(str(payload["period_end"])),
            is_correction=bool(payload["is_correction"]),
            section_title=str(payload["section_title"]),
            section_level=int(payload["section_level"]),
            section_order=int(payload["section_order"]),
            heading_path=tuple(str(value) for value in payload["heading_path"]),
            source_file=str(payload["source_file"]),
            chunk_index=int(payload["chunk_index"]),
            text=str(payload["text"]),
        )
