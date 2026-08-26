"""Provide an HTTP client for the OpenAI Embeddings API."""

from typing import Any, Optional

import httpx


BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingClient:
    """Convert text into vectors through the OpenAI Embeddings API."""

    def __init__(
        self,
        api_key: str,
        model_name: str = DEFAULT_MODEL,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        """Initialize the client with API credentials and a model.

        Args:
            api_key: OpenAI API key used for authentication.
            model_name: Embedding model sent to the API.
            http_client: Optional HTTP client used for testing.
        """
        if not api_key:
            raise ValueError("api_key must not be empty")

        self._api_key = api_key
        self.model_name = model_name
        self._client = http_client or httpx.Client(timeout=60.0)
        self._owns_client = http_client is None

    def close(self) -> None:
        """Close the internally created HTTP connection pool."""
        if self._owns_client:
            self._client.close()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each input text.

        Args:
            texts: Non-empty text strings to embed.

        Returns:
            Embedding vectors in the same order as the input texts.

        Raises:
            ValueError: If an input text is empty.
            RuntimeError: If the API request or response is invalid.
        """
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("embedding input texts must not be empty")

        response = self._client.post(
            f"{BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "input": texts,
                "model": self.model_name,
                "encoding_format": "float",
            },
        )
        if response.status_code != 200:
            raise RuntimeError(self._read_error(response))

        data = response.json().get("data")
        if not isinstance(data, list):
            raise RuntimeError("OpenAI embedding response has no data list")

        try:
            ordered = sorted(data, key=lambda item: item["index"])
            return [item["embedding"] for item in ordered]
        except (KeyError, TypeError):
            raise RuntimeError("OpenAI embedding response has invalid data") from None

    @staticmethod
    def _read_error(response: httpx.Response) -> str:
        """Return a readable API error message."""
        try:
            payload: dict[str, Any] = response.json()
            message = payload.get("error", {}).get("message")
        except (TypeError, ValueError):
            message = None
        return message or (
            f"OpenAI embedding request failed with status {response.status_code}"
        )
