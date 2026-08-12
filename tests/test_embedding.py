"""Test batch embedding for document chunks."""

import unittest
from datetime import date, datetime

from finrag.processing.chunker import DocumentChunk
from finrag.processing.embedding import embed_chunks


class FakeEmbeddingClient:
    """Return deterministic vectors without calling an external API."""

    model_name = "fake-embedding-model"

    def __init__(self) -> None:
        """Initialize the recorded API calls."""
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Create a three-dimensional vector for each input text."""
        self.calls.append(texts)
        return [
            [float(len(text)), float(index), 1.0]
            for index, text in enumerate(texts)
        ]


class InvalidEmbeddingClient:
    """Return vectors with inconsistent dimensions."""

    model_name = "invalid-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one invalid vector per input text."""
        return [[1.0] if index == 0 else [1.0, 2.0] for index, _ in enumerate(texts)]


class EmbeddingTest(unittest.TestCase):
    """Verify batching, metadata retention, and vector validation."""

    def test_embeds_chunks_in_batches_and_keeps_source_chunk(self) -> None:
        """Call the client in batches and retain each original chunk."""
        chunks = [self._make_chunk(index) for index in range(1, 4)]
        client = FakeEmbeddingClient()

        embedded = embed_chunks(chunks, client, batch_size=2)

        self.assertEqual(client.calls, [["text 1", "text 2"], ["text 3"]])
        self.assertEqual([item.chunk for item in embedded], chunks)
        self.assertEqual(embedded[0].vector, (6.0, 0.0, 1.0))
        self.assertEqual(embedded[0].embedding_model, "fake-embedding-model")
        self.assertEqual(embedded[0].embedding_dimension, 3)

    def test_returns_empty_result_without_calling_client(self) -> None:
        """Skip the client when no chunks are provided."""
        client = FakeEmbeddingClient()

        embedded = embed_chunks([], client)

        self.assertEqual(embedded, [])
        self.assertEqual(client.calls, [])

    def test_rejects_inconsistent_vector_dimensions(self) -> None:
        """Reject vectors that cannot share one database index."""
        chunks = [self._make_chunk(index) for index in range(1, 3)]

        with self.assertRaisesRegex(ValueError, "same dimension"):
            embed_chunks(chunks, InvalidEmbeddingClient())

    def test_rejects_wrong_number_of_vectors(self) -> None:
        """Reject a response that does not match the input batch."""

        class MissingVectorClient:
            """Return fewer vectors than requested."""

            model_name = "missing-vector-model"

            def embed(self, texts: list[str]) -> list[list[float]]:
                """Return no vectors for the input batch."""
                return []

        with self.assertRaisesRegex(ValueError, "one vector per text"):
            embed_chunks([self._make_chunk(1)], MissingVectorClient())

    @staticmethod
    def _make_chunk(index: int) -> DocumentChunk:
        """Create one document chunk for a test case."""
        return DocumentChunk(
            chunk_id=f"S1000001:3:{index}",
            company_name="Example Company",
            edinet_code="E00001",
            doc_id="S1000001",
            logical_report_id="E00001:2024-04-01:2025-03-31:annual",
            document_type="annual_securities_report",
            submitted_at=datetime(2025, 6, 1, 9, 0),
            period_start=date(2024, 4, 1),
            period_end=date(2025, 3, 31),
            is_correction=False,
            section_title="３【事業等のリスク】",
            section_level=3,
            section_order=3,
            heading_path=(
                "第一部【企業情報】",
                "３【事業等のリスク】",
            ),
            source_file="XBRL/PublicDoc/example_ixbrl.htm",
            chunk_index=index,
            text=f"text {index}",
        )


if __name__ == "__main__":
    unittest.main()
