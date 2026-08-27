"""Test section-aware chunk creation for EDINET reports."""

import unittest
from datetime import date, datetime
from pathlib import Path

from finrag.ingestion.identifier import FilingIdentity
from finrag.ingestion.section_extractor import DocumentSection
from finrag.processing.chunker import create_chunks


class ChunkerTest(unittest.TestCase):
    """Verify chunk boundaries, overlap, and inherited metadata."""

    def test_keeps_short_section_as_one_chunk_with_metadata(self) -> None:
        """Keep short text intact and copy its report and section metadata."""
        filing = self._make_filing()
        section = self._make_section("短い本文です。")

        chunks = create_chunks(filing, [section], max_chars=50, overlap_chars=10)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_id, "S1000001:3:1")
        self.assertEqual(chunks[0].company_name, "Example Company")
        self.assertEqual(chunks[0].heading_path, section.heading_path)
        self.assertEqual(chunks[0].text, "短い本文です。")

    def test_splits_long_section_with_overlap_and_size_limit(self) -> None:
        """Split at sentence boundaries and retain trailing context."""
        filing = self._make_filing()
        section = self._make_section(
            "市場環境が変化しています。"
            "為替変動の影響があります。"
            "重要な人材の確保が必要です。"
        )

        chunks = create_chunks(filing, [section], max_chars=35, overlap_chars=8)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.text) <= 35 for chunk in chunks))
        self.assertEqual(
            [chunk.chunk_index for chunk in chunks],
            list(range(1, len(chunks) + 1)),
        )
        self.assertTrue(chunks[1].text.startswith(chunks[0].text[-8:]))

    def test_splits_long_table_text_without_sentence_marks(self) -> None:
        """Fall back to safe lengths when text has no sentence boundary."""
        filing = self._make_filing()
        section = self._make_section("売上高 100 200 300 400 500 600 700")

        chunks = create_chunks(filing, [section], max_chars=18, overlap_chars=0)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.text) <= 18 for chunk in chunks))

    def test_overlap_does_not_exceed_size_limit(self) -> None:
        """Reserve space for both overlap text and its separator."""
        filing = self._make_filing()
        section = self._make_section("あ" * 60)

        chunks = create_chunks(filing, [section], max_chars=18, overlap_chars=8)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.text) <= 18 for chunk in chunks))
        self.assertTrue(chunks[1].text.startswith(chunks[0].text[-8:]))

    @staticmethod
    def _make_filing() -> FilingIdentity:
        """Create a minimal identified filing for a test case."""
        return FilingIdentity(
            company_name="Example Company",
            edinet_code="E00001",
            doc_id="S1000001",
            document_type="annual_securities_report",
            doc_type_code="120",
            submitted_at=datetime(2025, 6, 1, 9, 0),
            period_start=date(2024, 4, 1),
            period_end=date(2025, 3, 31),
            is_correction=False,
            parent_doc_id=None,
            source_dir=Path("data/raw/edinet/E00001/S1000001"),
        )

    @staticmethod
    def _make_section(text: str) -> DocumentSection:
        """Create a structured section for a test case."""
        return DocumentSection(
            title="３【事業等のリスク】",
            level=3,
            order=3,
            heading_path=(
                "第一部【企業情報】",
                "第２【事業の状況】",
                "３【事業等のリスク】",
            ),
            source_file="XBRL/PublicDoc/0102010_honbun_example_ixbrl.htm",
            text=text,
        )


if __name__ == "__main__":
    unittest.main()
