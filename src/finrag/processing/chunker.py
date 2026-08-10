"""Split structured EDINET sections into retrieval chunks."""

import re
from dataclasses import dataclass
from datetime import date, datetime

from finrag.ingestion.identifier import FilingIdentity
from finrag.ingestion.section_extractor import DocumentSection


DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP_CHARS = 100
SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？])")


@dataclass(frozen=True)
class DocumentChunk:
    """Store retrieval text with its report and section metadata."""

    chunk_id: str
    company_name: str
    edinet_code: str
    doc_id: str
    logical_report_id: str
    document_type: str
    submitted_at: datetime
    period_start: date
    period_end: date
    is_correction: bool
    section_title: str
    section_level: int
    section_order: int
    heading_path: tuple[str, ...]
    source_file: str
    chunk_index: int
    text: str


def create_chunks(
    filing: FilingIdentity,
    sections: list[DocumentSection],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[DocumentChunk]:
    """Split report sections into chunks without crossing section boundaries.

    Args:
        filing: Identified filing that owns the sections.
        sections: Structured report sections to split.
        max_chars: Maximum number of characters in one chunk.
        overlap_chars: Maximum context copied from the previous chunk.

    Returns:
        Ordered chunks containing report and section metadata.

    Raises:
        ValueError: If the chunk size settings are invalid.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be between 0 and max_chars")
    if overlap_chars and max_chars - overlap_chars <= 1:
        raise ValueError("chunk size must leave room for non-overlap text")

    chunks = []
    for section in sections:
        texts = _split_text(section.text, max_chars, overlap_chars)
        for chunk_index, text in enumerate(texts, start=1):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{filing.doc_id}:{section.order}:{chunk_index}",
                    company_name=filing.company_name,
                    edinet_code=filing.edinet_code,
                    doc_id=filing.doc_id,
                    logical_report_id=filing.logical_report_id,
                    document_type=filing.document_type,
                    submitted_at=filing.submitted_at,
                    period_start=filing.period_start,
                    period_end=filing.period_end,
                    is_correction=filing.is_correction,
                    section_title=section.title,
                    section_level=section.level,
                    section_order=section.order,
                    heading_path=section.heading_path,
                    source_file=section.source_file,
                    chunk_index=chunk_index,
                    text=text,
                )
            )
    return chunks


def _split_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split text at sentence boundaries with optional character overlap."""
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    separator_chars = 1 if overlap_chars else 0
    target_chars = max_chars - overlap_chars - separator_chars
    sentences = [
        sentence.strip()
        for sentence in SENTENCE_BOUNDARY.split(text)
        if sentence.strip()
    ]
    parts = []
    for sentence in sentences:
        parts.extend(_split_long_part(sentence, target_chars))

    base_chunks = _pack_parts(parts, target_chars)
    if overlap_chars == 0:
        return base_chunks

    chunks = [base_chunks[0]]
    for previous, current in zip(base_chunks, base_chunks[1:]):
        overlap = _read_overlap(previous, overlap_chars)
        chunks.append(f"{overlap} {current}".strip())
    return chunks


def _split_long_part(text: str, max_chars: int) -> list[str]:
    """Split text that has no usable sentence boundary."""
    parts = []
    remaining = text

    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at <= 0:
            split_at = max_chars
        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        parts.append(remaining)
    return parts


def _pack_parts(parts: list[str], max_chars: int) -> list[str]:
    """Pack short text parts into chunks up to the target size."""
    chunks = []
    current = ""

    for part in parts:
        candidate = f"{current} {part}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = part
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks


def _read_overlap(text: str, max_chars: int) -> str:
    """Return trailing context without exceeding the overlap limit."""
    if len(text) <= max_chars:
        return text

    overlap = text[-max_chars:]
    first_space = overlap.find(" ")
    if first_space >= 0:
        overlap = overlap[first_space + 1 :]
    return overlap
