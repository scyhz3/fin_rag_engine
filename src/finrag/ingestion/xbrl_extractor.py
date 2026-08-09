"""Extract readable text pages from EDINET Inline XBRL files."""

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from lxml import html

from finrag.ingestion.identifier import FilingIdentity


@dataclass(frozen=True)
class XbrlPage:
    """Store readable text and source information for one XBRL body file."""

    source_file: str
    order: int
    text: str


def extract_xbrl_pages(filing: FilingIdentity) -> list[XbrlPage]:
    """Extract ordered text pages from one filing's Inline XBRL body files.

    Args:
        filing: Identified filing whose document ZIP should be read.

    Returns:
        Readable XBRL body pages in document order.

    Raises:
        ValueError: If no readable XBRL body file is found.
    """
    zip_path = filing.source_dir / "document.zip"

    with ZipFile(zip_path) as archive:
        body_files = sorted(
            name
            for name in archive.namelist()
            if name.startswith("XBRL/PublicDoc/")
            and "_honbun_" in Path(name).name
            and name.endswith("_ixbrl.htm")
        )
        pages = [
            XbrlPage(
                source_file=name,
                order=_read_file_order(name),
                text=_extract_visible_text(archive.read(name)),
            )
            for name in body_files
        ]

    readable_pages = [page for page in pages if page.text]
    if not readable_pages:
        raise ValueError(f"No readable XBRL body found for {filing.doc_id}")
    return readable_pages


def _read_file_order(source_file: str) -> int:
    """Return the numeric order prefix from an XBRL body file name."""
    prefix = Path(source_file).name.split("_", 1)[0]
    if not prefix.isdigit():
        raise ValueError(f"Invalid XBRL body file name: {source_file}")
    return int(prefix)


def _extract_visible_text(content: bytes) -> str:
    """Return normalized visible text from one Inline XBRL document."""
    root = html.fromstring(content)

    for element in root.xpath("//script | //style"):
        element.drop_tree()

    lines = [" ".join(line.split()) for line in root.text_content().splitlines()]
    return "\n".join(line for line in lines if line)
