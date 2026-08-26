"""Test the OpenAI embedding HTTP client."""

import json
import unittest

import httpx

from finrag.processing.openai_embedding_client import OpenAIEmbeddingClient


class OpenAIEmbeddingClientTest(unittest.TestCase):
    """Verify request construction and response parsing."""

    def test_embeds_texts_and_restores_input_order(self) -> None:
        """Send one API request and order vectors by response index."""

        def handle(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual(request.url.path, "/v1/embeddings")
            self.assertEqual(
                request.headers["authorization"],
                "Bearer test-key",
            )
            self.assertEqual(
                payload,
                {
                    "input": [
                        "売上高が増加しました。",
                        "事業上のリスクです。",
                    ],
                    "model": "text-embedding-3-small",
                    "encoding_format": "float",
                },
            )
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"index": 1, "embedding": [0.3, 0.4]},
                        {"index": 0, "embedding": [0.1, 0.2]},
                    ]
                },
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handle))
        client = OpenAIEmbeddingClient("test-key", http_client=http_client)

        vectors = client.embed(
            ["売上高が増加しました。", "事業上のリスクです。"]
        )

        self.assertEqual(vectors, [[0.1, 0.2], [0.3, 0.4]])
        http_client.close()

    def test_returns_empty_result_without_request(self) -> None:
        """Skip the API when no text is provided."""

        def fail_if_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("HTTP request should not be sent")

        http_client = httpx.Client(
            transport=httpx.MockTransport(fail_if_called)
        )
        client = OpenAIEmbeddingClient("test-key", http_client=http_client)

        self.assertEqual(client.embed([]), [])
        http_client.close()

    def test_rejects_empty_text(self) -> None:
        """Reject input that the embedding API does not accept."""
        client = OpenAIEmbeddingClient("test-key")

        with self.assertRaisesRegex(ValueError, "must not be empty"):
            client.embed([" "])

        client.close()

    def test_raises_readable_api_error(self) -> None:
        """Expose the API error message without exposing credentials."""

        def handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                json={"error": {"message": "Rate limit reached"}},
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handle))
        client = OpenAIEmbeddingClient("test-key", http_client=http_client)

        with self.assertRaisesRegex(RuntimeError, "Rate limit reached"):
            client.embed(["text"])

        http_client.close()


if __name__ == "__main__":
    unittest.main()
