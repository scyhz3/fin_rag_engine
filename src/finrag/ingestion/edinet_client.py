"""Provide a small HTTP client for the EDINET API."""

from datetime import date
from typing import Any

import httpx


BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"


class EdinetClient:
    """Make HTTP requests to the EDINET API."""

    def __init__(self, api_key: str) -> None:
        """Initialize the client with an EDINET API key.

        Args:
            api_key: Subscription key used to authenticate EDINET API requests.
        """
        self.api_key = api_key
        self._client = httpx.Client(timeout=60.0)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def list_documents(self, target_date: date) -> list[dict[str, Any]]:
        """Return EDINET document metadata published for one date.

        Args:
            target_date: Date whose document list should be requested.

        Returns:
            Metadata dictionaries returned by the EDINET document list API.
        """
        response = self._client.get(
            f"{BASE_URL}/documents.json",
            params={
                "date": target_date.isoformat(),
                "type": 2,
                "Subscription-Key": self.api_key,
            },
        )
        self._raise_for_error(response)

        payload = response.json()
        return payload.get("results", [])

    def download_document(self, doc_id: str, document_type: int) -> bytes:
        """Download one EDINET document in the requested format.

        Args:
            doc_id: EDINET document identifier.
            document_type: EDINET download type, such as 1 for ZIP or 2 for PDF.

        Returns:
            Raw bytes of the downloaded document.
        """
        response = self._client.get(
            f"{BASE_URL}/documents/{doc_id}",
            params={
                "type": document_type,
                "Subscription-Key": self.api_key,
            },
        )
        self._raise_for_error(response)

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            message = response.json().get("message", "Unknown EDINET API error")
            raise RuntimeError(message)

        return response.content

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        """Raise a runtime error when an EDINET request was unsuccessful.

        Args:
            response: HTTP response to validate.
        """
        if response.status_code != 200:
            raise RuntimeError(
                f"EDINET API request failed with status {response.status_code}"
            )
