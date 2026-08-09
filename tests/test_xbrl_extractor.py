"""Test readable text extraction from EDINET Inline XBRL files."""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from finrag.ingestion.identifier import FilingIdentity
from finrag.ingestion.xbrl_extractor import extract_xbrl_pages


class XbrlExtractorTest(unittest.TestCase):
    """Verify XBRL body selection, ordering, and text cleanup."""

    def test_extracts_only_ordered_readable_body_pages(self) -> None:
        """Ignore non-body files and return normalized pages in order."""
        with tempfile.TemporaryDirectory() as directory:
            filing_dir = Path(directory) / "E00001" / "S1000001"
            filing_dir.mkdir(parents=True)
            self._write_document_zip(filing_dir / "document.zip")

            pages = extract_xbrl_pages(self._make_filing(filing_dir))

            self.assertEqual([page.order for page in pages], [101010, 102010])
            self.assertEqual(
                [Path(page.source_file).name[:7] for page in pages],
                ["0101010", "0102010"],
            )
            self.assertEqual(
                pages[0].text,
                "第一部 企業情報\n売上高 100 百万円",
            )
            self.assertEqual(
                pages[1].text,
                "第二部 提出会社の保証会社等の情報",
            )
            self.assertNotIn("hidden style", pages[0].text)
            self.assertNotIn("hidden script", pages[0].text)

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
        """Create a ZIP containing body and non-body XBRL files."""
        first_page = """
        <html>
          <head>
            <meta charset="utf-8">
            <style>hidden style</style>
            <script>hidden script</script>
          </head>
          <body>
            <p> 第一部   企業情報 </p>
            <p>売上高 <ix:nonNumeric>100</ix:nonNumeric> 百万円</p>
          </body>
        </html>
        """
        second_page = """
        <html>
          <head><meta charset="utf-8"></head>
          <body>
            <p>第二部 提出会社の保証会社等の情報</p>
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
            archive.writestr(
                "XBRL/PublicDoc/0000000_header_example_ixbrl.htm",
                "<html><body>header</body></html>",
            )
            archive.writestr(
                "XBRL/PublicDoc/0103010_honbun_example.xml",
                "<xml>not inline XBRL</xml>",
            )


if __name__ == "__main__":
    unittest.main()
