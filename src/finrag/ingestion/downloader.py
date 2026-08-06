import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator

from finrag.ingestion.edinet_client import EdinetClient


class EdinetDownloader:
    """Find and download EDINET filings for selected companies."""

    def __init__(
        self,
        client: EdinetClient,
        raw_dir: Path,
        edinet_codes: set[str],
    ) -> None:
        self.client = client
        self.raw_dir = raw_dir
        self.edinet_codes = edinet_codes

    def find_filings(
        self,
        start_date: date,
        end_date: date,
    ) -> Iterator[dict[str, Any]]:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        seen_doc_ids: set[str] = set()
        target_date = start_date

        while target_date <= end_date:
            for document in self.client.list_documents(target_date):
                doc_id = document.get("docID")
                if self._is_target_filing(document) and doc_id not in seen_doc_ids:
                    seen_doc_ids.add(doc_id)
                    yield document

            target_date += timedelta(days=1)
            if target_date <= end_date:
                time.sleep(0.2)

    def download_filing(self, metadata: dict[str, Any]) -> Path:
        doc_id = metadata["docID"]
        edinet_code = metadata["edinetCode"]
        document_dir = self.raw_dir / edinet_code / doc_id
        document_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = document_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        zip_path = document_dir / "document.zip"
        if metadata.get("xbrlFlag") == "1" and not zip_path.exists():
            zip_path.write_bytes(self.client.download_document(doc_id, 1))

        pdf_path = document_dir / "document.pdf"
        if metadata.get("pdfFlag") == "1" and not pdf_path.exists():
            pdf_path.write_bytes(self.client.download_document(doc_id, 2))

        return document_dir

    def download_range(self, start_date: date, end_date: date) -> list[Path]:
        return [
            self.download_filing(metadata)
            for metadata in self.find_filings(start_date, end_date)
        ]

    def _is_target_filing(self, document: dict[str, Any]) -> bool:
        return (
            document.get("edinetCode") in self.edinet_codes
            and document.get("docTypeCode") in {"120", "130"}
            and document.get("withdrawalStatus") == "0"
            and document.get("disclosureStatus") == "0"
            and document.get("legalStatus") in {"1", "2"}
        )
