"""Test local Qdrant persistence and filtered search."""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from finrag.processing.chunker import DocumentChunk
from finrag.processing.embedding import EmbeddedChunk
from finrag.storage.qdrant_vector_store import QdrantVectorStore
from finrag.storage.vector_store import SearchFilters


class QdrantVectorStoreTest(unittest.TestCase):
    """Verify upsert, persistence, filtering, and model validation."""

    def test_persists_and_filters_similar_chunks(self) -> None:
        """Return only similar chunks inside the requested report scope."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qdrant"
            store = QdrantVectorStore(path)
            store.upsert(
                [
                    self._make_embedded(1, "E02655", (0.9, 0.1), "事業リスク"),
                    self._make_embedded(2, "E02655", (0.1, 0.9), "売上高"),
                    self._make_embedded(3, "E99999", (1.0, 0.0), "他社リスク"),
                ]
            )
            store.close()

            reopened = QdrantVectorStore(path)
            results = reopened.search(
                [1.0, 0.0],
                filters=SearchFilters(
                    edinet_code="E02655",
                    period_end=date(2025, 3, 31),
                    document_type="annual_securities_report",
                ),
                top_k=5,
            )
            reopened.close()

        self.assertEqual(
            [result.chunk.text for result in results],
            ["事業リスク", "売上高"],
        )
        self.assertGreater(results[0].score, results[1].score)
        self.assertEqual(results[0].chunk.edinet_code, "E02655")

    def test_upsert_replaces_chunk_with_the_same_id(self) -> None:
        """Replace an existing point instead of creating a duplicate."""
        with tempfile.TemporaryDirectory() as directory:
            store = QdrantVectorStore(Path(directory) / "qdrant")
            store.upsert([self._make_embedded(1, "E02655", (1.0, 0.0), "old")])
            store.upsert([self._make_embedded(1, "E02655", (0.0, 1.0), "new")])

            results = store.search([0.0, 1.0], top_k=10)
            store.close()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk.text, "new")

    def test_rejects_a_different_model_in_one_collection(self) -> None:
        """Prevent vectors from different embedding spaces from mixing."""
        with tempfile.TemporaryDirectory() as directory:
            store = QdrantVectorStore(Path(directory) / "qdrant")
            store.upsert([self._make_embedded(1, "E02655", (1.0, 0.0), "text")])
            different = self._make_embedded(
                2,
                "E02655",
                (0.0, 1.0),
                "text",
                model_name="another-model",
            )

            with self.assertRaisesRegex(ValueError, "model"):
                store.upsert([different])

            store.close()

    @staticmethod
    def _make_embedded(
        index: int,
        edinet_code: str,
        vector: tuple[float, ...],
        text: str,
        model_name: str = "test-model",
    ) -> EmbeddedChunk:
        """Create one embedded chunk for a test case."""
        chunk = DocumentChunk(
            chunk_id=f"S1000001:3:{index}",
            company_name="Example Company",
            edinet_code=edinet_code,
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
            text=text,
        )
        return EmbeddedChunk(
            chunk=chunk,
            vector=vector,
            embedding_model=model_name,
            embedding_dimension=len(vector),
        )


if __name__ == "__main__":
    unittest.main()
