"""Test the local Ruri embedding client."""

import unittest

from finrag.processing.ruri_embedding_client import RuriEmbeddingClient


class FakeSentenceEmbeddingModel:
    """Record model input and return deterministic vectors."""

    def __init__(self) -> None:
        """Initialize the recorded model calls."""
        self.calls = []

    def encode(
        self,
        texts: list[str],
        **kwargs: object,
    ) -> list[list[float]]:
        """Return one normalized-looking vector per input text."""
        self.calls.append((texts, kwargs))
        return [[float(index), 1.0] for index, _ in enumerate(texts)]


class RuriEmbeddingClientTest(unittest.TestCase):
    """Verify retrieval prefixes and local vector conversion."""

    def test_embeds_documents_with_document_prefix(self) -> None:
        """Prefix document text according to the Ruri model contract."""
        model = FakeSentenceEmbeddingModel()
        client = RuriEmbeddingClient(model=model)

        vectors = client.embed(
            ["売上高が増加しました。", "事業リスクです。"]
        )

        self.assertEqual(vectors, [[0.0, 1.0], [1.0, 1.0]])
        self.assertEqual(
            model.calls[0][0],
            [
                "検索文書: 売上高が増加しました。",
                "検索文書: 事業リスクです。",
            ],
        )
        self.assertEqual(
            model.calls[0][1],
            {"normalize_embeddings": True, "show_progress_bar": False},
        )

    def test_embeds_query_with_query_prefix(self) -> None:
        """Use the query prefix for later similarity search."""
        model = FakeSentenceEmbeddingModel()
        client = RuriEmbeddingClient(model=model)

        vector = client.embed_query("主要な事業リスクは何ですか？")

        self.assertEqual(vector, [0.0, 1.0])
        self.assertEqual(
            model.calls[0][0],
            ["検索クエリ: 主要な事業リスクは何ですか？"],
        )

    def test_returns_empty_result_without_model_call(self) -> None:
        """Skip local inference when no documents are provided."""
        model = FakeSentenceEmbeddingModel()
        client = RuriEmbeddingClient(model=model)

        self.assertEqual(client.embed([]), [])
        self.assertEqual(model.calls, [])

    def test_rejects_empty_text(self) -> None:
        """Reject empty document and query text."""
        client = RuriEmbeddingClient(model=FakeSentenceEmbeddingModel())

        with self.assertRaisesRegex(ValueError, "must not be empty"):
            client.embed([" "])
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            client.embed_query("")


if __name__ == "__main__":
    unittest.main()
