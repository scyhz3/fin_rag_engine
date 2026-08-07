"""Test EDINET filing identification and version selection."""

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from finrag.ingestion.identifier import identify_filing, select_current_filings


class FilingIdentifierTest(unittest.TestCase):
    """Verify metadata identification and correction selection."""

    def test_identifies_correction_period_from_xbrl(self) -> None:
        """Use XBRL dates when correction metadata has no accounting period."""
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            filing_dir = self._write_filing(
                raw_dir,
                doc_id="S1000002",
                doc_type_code="130",
                submitted_at="2025-07-01 09:00",
                parent_doc_id="S1000001",
                include_metadata_period=False,
            )

            filing = identify_filing(filing_dir)

            self.assertEqual(filing.company_name, "Example Company")
            self.assertEqual(filing.edinet_code, "E00001")
            self.assertEqual(filing.doc_id, "S1000002")
            self.assertEqual(filing.document_type, "annual_securities_report")
            self.assertEqual(filing.period_start.isoformat(), "2024-04-01")
            self.assertEqual(filing.period_end.isoformat(), "2025-03-31")
            self.assertTrue(filing.is_correction)
            self.assertEqual(filing.logical_report_id, "S1000001")

    def test_selects_latest_correction_only(self) -> None:
        """Keep only the latest correction from one original-report group."""
        with tempfile.TemporaryDirectory() as directory:
            raw_dir = Path(directory)
            original = identify_filing(
                self._write_filing(
                    raw_dir,
                    doc_id="S1000001",
                    doc_type_code="120",
                    submitted_at="2025-06-01 09:00",
                )
            )
            first_correction = identify_filing(
                self._write_filing(
                    raw_dir,
                    doc_id="S1000002",
                    doc_type_code="130",
                    submitted_at="2025-07-01 09:00",
                    parent_doc_id="S1000001",
                )
            )
            latest_correction = identify_filing(
                self._write_filing(
                    raw_dir,
                    doc_id="S1000003",
                    doc_type_code="130",
                    submitted_at="2025-08-01 09:00",
                    parent_doc_id="S1000001",
                )
            )

            selected = select_current_filings(
                [original, latest_correction, first_correction]
            )

            self.assertEqual([filing.doc_id for filing in selected], ["S1000003"])

    @staticmethod
    def _write_filing(
        raw_dir: Path,
        doc_id: str,
        doc_type_code: str,
        submitted_at: str,
        parent_doc_id: str = "",
        include_metadata_period: bool = True,
    ) -> Path:
        """Create a minimal saved filing for a test case."""
        filing_dir = raw_dir / "E00001" / doc_id
        filing_dir.mkdir(parents=True)

        metadata = {
            "docID": doc_id,
            "edinetCode": "E00001",
            "filerName": "Example Company",
            "docTypeCode": doc_type_code,
            "submitDateTime": submitted_at,
            "periodStart": "2024-04-01" if include_metadata_period else None,
            "periodEnd": "2025-03-31" if include_metadata_period else None,
            "parentDocID": parent_doc_id or None,
        }
        (filing_dir / "metadata.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )

        header = """
        <html>
          <body>
            <ix:nonNumeric name="jpdei_cor:EDINETCodeDEI">E00001</ix:nonNumeric>
            <ix:nonNumeric name="jpdei_cor:FilerNameInJapaneseDEI">
              Example Company
            </ix:nonNumeric>
            <ix:nonNumeric name="jpdei_cor:CurrentFiscalYearStartDateDEI">
              2024-04-01
            </ix:nonNumeric>
            <ix:nonNumeric name="jpdei_cor:CurrentFiscalYearEndDateDEI">
              2025-03-31
            </ix:nonNumeric>
          </body>
        </html>
        """
        header_name = (
            "XBRL/PublicDoc/"
            "0000000_header_jpcrp030000-asr-001_E00001_2025_ixbrl.htm"
        )
        with ZipFile(filing_dir / "document.zip", "w", ZIP_DEFLATED) as archive:
            archive.writestr(header_name, header)

        return filing_dir


if __name__ == "__main__":
    unittest.main()
