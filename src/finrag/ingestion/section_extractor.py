"""Extract structured sections from EDINET Inline XBRL body files."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from lxml import html
from lxml.html import HtmlElement

from finrag.ingestion.identifier import FilingIdentity


HEADING_TAGS = {f"h{level}" for level in range(1, 7)}


@dataclass(frozen=True)
class DocumentSection:
    """Store one structured report section and its heading hierarchy."""

    title: str
    level: int
    order: int
    heading_path: tuple[str, ...]
    source_file: str
    text: str


@dataclass
class _SectionBuilder:
    """Collect text while one section is being parsed."""

    title: str
    level: int
    heading_path: tuple[str, ...]
    source_file: str
    text_parts: list[str]


def extract_sections(filing: FilingIdentity) -> list[DocumentSection]:
    """Extract ordered sections from one filing's Inline XBRL body files.

    Args:
        filing: Identified filing whose document ZIP should be read.

    Returns:
        Non-empty report sections in document order.

    Raises:
        ValueError: If no readable section is found.
    """
    zip_path = filing.source_dir / "document.zip"
    heading_stack: list[str] = []
    sections: list[DocumentSection] = []

    with ZipFile(zip_path) as archive:
        body_files = sorted(
            name
            for name in archive.namelist()
            if name.startswith("XBRL/PublicDoc/")
            and "_honbun_" in Path(name).name
            and name.endswith("_ixbrl.htm")
        )

        for source_file in body_files:
            file_sections = _extract_file_sections(
                archive.read(source_file),
                source_file,
                heading_stack,
            )
            for section in file_sections:
                text = _normalize_text(" ".join(section.text_parts))
                if text:
                    sections.append(
                        DocumentSection(
                            title=section.title,
                            level=section.level,
                            order=len(sections) + 1,
                            heading_path=section.heading_path,
                            source_file=section.source_file,
                            text=text,
                        )
                    )

    if not sections:
        raise ValueError(f"No readable XBRL section found for {filing.doc_id}")
    return sections


def _extract_file_sections(
    content: bytes,
    source_file: str,
    heading_stack: list[str],
) -> list[_SectionBuilder]:
    """Extract section builders from one Inline XBRL body file."""
    root = html.fromstring(content)
    for element in root.xpath("//script | //style"):
        element.drop_tree()

    sections: list[_SectionBuilder] = []
    current: Optional[_SectionBuilder] = None

    def visit(element: HtmlElement) -> None:
        nonlocal current

        tag = element.tag.lower() if isinstance(element.tag, str) else ""
        if tag in HEADING_TAGS:
            title = _normalize_text(element.text_content())
            if title:
                level = int(tag[1])
                del heading_stack[level - 1 :]
                heading_stack.append(title)
                current = _SectionBuilder(
                    title=title,
                    level=level,
                    heading_path=tuple(heading_stack),
                    source_file=source_file,
                    text_parts=[],
                )
                sections.append(current)
            return

        if current is not None and element.text:
            current.text_parts.append(element.text)

        for child in element:
            visit(child)
            if current is not None and child.tail:
                current.text_parts.append(child.tail)

    visit(root)
    return sections


def _normalize_text(text: str) -> str:
    """Collapse repeated whitespace in a title or section body."""
    return " ".join(text.split())
