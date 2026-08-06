from datetime import date
from typing import Any

import httpx


BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"


class EdinetClient:
    """Make HTTP requests to the EDINET API."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._client.close()

    def list_documents(self, target_date: date) -> list[dict[str, Any]]:
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
        if response.status_code != 200:
            raise RuntimeError(
                f"EDINET API request failed with status {response.status_code}"
            )
