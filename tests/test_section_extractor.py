"""Test section extraction from EDINET Inline XBRL files."""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from finrag.ingestion.identifier import FilingIdentity
from finrag.ingestion.section_extractor import extract_sections


class SectionExtractorTest(unittest.TestCase):
    """Verify heading hierarchy, text ownership, and document order."""

    def test_extracts_non_empty_sections_with_heading_paths(self) -> None:
        """Keep body text under its closest heading and full heading path."""
        with tempfile.TemporaryDirectory() as directory:
            filing_dir = Path(directory) / "E00001" / "S1000001"
            filing_dir.mkdir(parents=True)
            self._write_document_zip(filing_dir / "document.zip")

            sections = extract_sections(self._make_filing(filing_dir))

            self.assertEqual(
                [section.title for section in sections],
                [
                    "１【主要な経営指標】",
                    "２【事業等のリスク】",
                    "１【設備投資】",
                ],
            )
            self.assertEqual([section.order for section in sections], [1, 2, 3])
            self.assertEqual(
                sections[0].heading_path,
                (
                    "第一部【企業情報】",
                    "第１【企業の概況】",
                    "１【主要な経営指標】",
                ),
            )
            self.assertEqual(
                sections[2].heading_path,
                (
                    "第一部【企業情報】",
                    "第２【設備の状況】",
                    "１【設備投資】",
                ),
            )
            self.assertEqual(sections[0].text, "売上高 100 百万円")
            self.assertEqual(sections[1].text, "重要なリスクがあります。")
            self.assertNotIn("hidden script", sections[0].text)

    @staticmethod
    def _make_filing(filing_dir: Path) -> FilingIdentity:
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
            source_dir=filing_dir,
        )

    @staticmethod
    def _write_document_zip(zip_path: Path) -> None:
        """Create ordered XBRL body files with nested headings."""
        first_page = """
        <html>
          <head><meta charset="utf-8"></head>
          <body>
            <h1>第一部【企業情報】</h1>
            <h2>第１【企業の概況】</h2>
            <h3>１【主要な経営指標】</h3>
            <p>売上高 <ix:nonNumeric>100</ix:nonNumeric> 百万円</p>
            <script>hidden script</script>
            <h3>２【事業等のリスク】</h3>
            <p>重要なリスクがあります。</p>
          </body>
        </html>
        """
        second_page = """
        <html>
          <head><meta charset="utf-8"></head>
          <body>
            <h2>第２【設備の状況】</h2>
            <h3>１【設備投資】</h3>
            <p>設備投資額は50百万円です。</p>
          </body>
        </html>
        """

        with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
            archive.writestr(
                "XBRL/PublicDoc/0102010_honbun_example_ixbrl.htm",
                second_page,
            )
            archive.writestr(
                "XBRL/PublicDoc/0101010_honbun_example_ixbrl.htm",
                first_page,
            )


if __name__ == "__main__":
    unittest.main()
