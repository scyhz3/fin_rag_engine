"""Identify EDINET filings from saved metadata and XBRL ZIP files."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from lxml import html

from finrag.type import DOCUMENT_TYPES, DEI_FIELDS


@dataclass(frozen=True)
class FilingIdentity:
    """Store the normalized identity of one EDINET filing."""

    company_name: str
    edinet_code: str
    doc_id: str
    document_type: str
    doc_type_code: str
    submitted_at: datetime
    period_start: date
    period_end: date
    is_correction: bool
    parent_doc_id: Optional[str]
    source_dir: Path

    @property
    def logical_report_id(self) -> str:
        """Return the shared identifier for an original report and corrections."""
        return self.parent_doc_id or self.doc_id


def identify_filing(document_dir: Path) -> FilingIdentity:
    """Identify one filing from its saved metadata and XBRL ZIP.

    Args:
        document_dir: Directory containing metadata.json and document.zip.

    Returns:
        Normalized filing identity.

    Raises:
        ValueError: If required metadata or XBRL identity fields are invalid.
    """
    metadata_path = document_dir / "metadata.json"
    zip_path = document_dir / "document.zip"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    dei_facts = _read_dei_facts(zip_path)

    doc_id = _required_text(metadata, "docID")
    edinet_code = _required_text(metadata, "edinetCode")
    company_name = _required_text(metadata, "filerName")
    doc_type_code = _required_text(metadata, "docTypeCode")

    if doc_type_code not in DOCUMENT_TYPES:
        raise ValueError(f"Unsupported docTypeCode: {doc_type_code}")
    if document_dir.name != doc_id:
        raise ValueError(f"Directory name does not match docID: {doc_id}")
    if document_dir.parent.name != edinet_code:
        raise ValueError(f"Directory name does not match edinetCode: {edinet_code}")

    _validate_dei_value(dei_facts, "EDINETCodeDEI", edinet_code)
    _validate_dei_value(dei_facts, "FilerNameInJapaneseDEI", company_name)

    is_correction = doc_type_code == "130"
    parent_doc_id = metadata.get("parentDocID") or None
    if is_correction and parent_doc_id is None:
        raise ValueError(f"Correction filing has no parentDocID: {doc_id}")

    period_start = _parse_date(
        metadata.get("periodStart")
        or dei_facts.get("CurrentFiscalYearStartDateDEI"),
        "periodStart",
    )
    period_end = _parse_date(
        metadata.get("periodEnd")
        or dei_facts.get("CurrentFiscalYearEndDateDEI"),
        "periodEnd",
    )
    if period_end < period_start:
        raise ValueError(f"Invalid accounting period for {doc_id}")

    submitted_at = datetime.strptime(
        _required_text(metadata, "submitDateTime"),
        "%Y-%m-%d %H:%M",
    )

    return FilingIdentity(
        company_name=company_name,
        edinet_code=edinet_code,
        doc_id=doc_id,
        document_type=DOCUMENT_TYPES[doc_type_code],
        doc_type_code=doc_type_code,
        submitted_at=submitted_at,
        period_start=period_start,
        period_end=period_end,
        is_correction=is_correction,
        parent_doc_id=parent_doc_id,
        source_dir=document_dir,
    )


def identify_filings(raw_dir: Path) -> list[FilingIdentity]:
    """Identify all locally saved EDINET filings.

    Args:
        raw_dir: Root directory containing EDINET company and document folders.

    Returns:
        Filing identities sorted by submission time and document ID.
    """
    filings = [
        identify_filing(metadata_path.parent)
        for metadata_path in raw_dir.glob("*/*/metadata.json")
    ]
    return sorted(filings, key=lambda filing: (filing.submitted_at, filing.doc_id))


def select_current_filings(
    filings: list[FilingIdentity],
) -> list[FilingIdentity]:
    """Select only the latest filing for each logical report.

    Args:
        filings: Original reports and correction reports to group.

    Returns:
        Latest filing from each original-report group.
    """
    current_by_report: dict[str, FilingIdentity] = {}

    for filing in filings:
        current = current_by_report.get(filing.logical_report_id)
        if current is None or (filing.submitted_at, filing.doc_id) > (
            current.submitted_at,
            current.doc_id,
        ):
            current_by_report[filing.logical_report_id] = filing

    return sorted(
        current_by_report.values(),
        key=lambda filing: (filing.edinet_code, filing.period_end, filing.doc_id),
    )


def _read_dei_facts(zip_path: Path) -> dict[str, str]:
    """Read selected document information facts from an XBRL ZIP.

    Args:
        zip_path: Path to an EDINET document ZIP.

    Returns:
        Selected DEI concept names and text values.
    """
    with ZipFile(zip_path) as archive:
        headers = [
            name
            for name in archive.namelist()
            if name.startswith("XBRL/PublicDoc/0000000_header_")
            and name.endswith("_ixbrl.htm")
        ]
        if len(headers) != 1:
            raise ValueError(f"Expected one XBRL header in {zip_path}")
        root = html.fromstring(archive.read(headers[0]))

    facts = {}
    for element in root.xpath("//*[@name]"):
        concept = element.get("name").rsplit(":", 1)[-1]
        value = element.text_content().strip()
        if concept in DEI_FIELDS and value:
            facts[concept] = value
    return facts


def _required_text(metadata: dict, field: str) -> str:
    """Return a required non-empty metadata value as text."""
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required metadata field: {field}")
    return value.strip()


def _parse_date(value: Optional[str], field: str) -> date:
    """Parse a required ISO date value."""
    if not value:
        raise ValueError(f"Missing required filing field: {field}")
    return date.fromisoformat(value)


def _validate_dei_value(
    dei_facts: dict[str, str],
    field: str,
    expected: str,
) -> None:
    """Validate a DEI value when the field is present in XBRL."""
    actual = dei_facts.get(field)
    if actual is not None and actual != expected:
        raise ValueError(f"XBRL {field} does not match metadata")
