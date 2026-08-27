"""Provide local Japanese embeddings with the Ruri model."""

from typing import Any, Optional, Protocol


DEFAULT_MODEL = "cl-nagoya/ruri-v3-310m"
DOCUMENT_PREFIX = "検索文書: "
QUERY_PREFIX = "検索クエリ: "


class SentenceEmbeddingModel(Protocol):
    """Define the model method used by the local client."""

    def encode(self, texts: list[str], **kwargs: Any) -> Any:
        """Return embedding vectors for input texts."""
        ...


class RuriEmbeddingClient:
    """Generate Japanese retrieval vectors on the local machine."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        model: Optional[SentenceEmbeddingModel] = None,
    ) -> None:
        """Load a Ruri sentence embedding model.

        Args:
            model_name: Hugging Face model identifier or local model path.
            device: Optional inference device, such as cpu or mps.
            model: Optional preloaded model used for testing.

        Raises:
            RuntimeError: If local embedding dependencies are unavailable.
        """
        self.model_name = model_name
        self._model = model or self._load_model(model_name, device)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate document vectors for the embedding pipeline."""
        return self._encode(texts, DOCUMENT_PREFIX)

    def embed_query(self, text: str) -> list[float]:
        """Generate one query vector for retrieval."""
        if not text.strip():
            raise ValueError("embedding query must not be empty")
        return self._encode([text], QUERY_PREFIX)[0]

    def _encode(self, texts: list[str], prefix: str) -> list[list[float]]:
        """Prefix, normalize, and convert model output to Python floats."""
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("embedding input texts must not be empty")

        vectors = self._model.encode(
            [f"{prefix}{text}" for text in texts],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        values = vectors.tolist() if hasattr(vectors, "tolist") else vectors
        return [[float(value) for value in vector] for vector in values]

    @staticmethod
    def _load_model(
        model_name: str,
        device: Optional[str],
    ) -> SentenceEmbeddingModel:
        """Load the model from Hugging Face or the local cache."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError(
                "install local embedding dependencies with "
                "'uv sync --extra local-embedding'"
            ) from None

        return SentenceTransformer(model_name, device=device)
