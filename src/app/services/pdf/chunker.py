"""
PDF Chunking.

Splits a cleaned PdfDocument into LLM-sized chunks, preferring the PDF's
own structure (top-level table-of-contents entries) as chunk boundaries
and falling back to a character-budget window over pages when no usable
structure is present. Each chunk retains its source page numbers for
later provenance.

Maps to doc/pdf-extraction.md Stages 8-9. Structure detection here is
intentionally minimal (TOC only, no font-size/position heuristics) since
there is no consumer for finer-grained structure yet.
"""

from typing import Dict, List

from src.app.core.config import get_settings
from src.app.schemas.pdf import PdfChunk, PdfDocument, PdfPage, PdfTocEntry


def chunk_document(document: PdfDocument) -> List[PdfChunk]:
    """Splits `document` into chunks, aligned to chapters when a TOC exists."""
    top_level_entries = [entry for entry in document.metadata.toc if entry.level == 1]

    if top_level_entries:
        return _chunk_by_toc(document.pages, top_level_entries)
    return _chunk_by_window(document.pages)


def _chunk_by_toc(pages: List[PdfPage], entries: List[PdfTocEntry]) -> List[PdfChunk]:
    ordered_entries = sorted(entries, key=lambda e: e.page_number)
    pages_by_number: Dict[int, PdfPage] = {p.page_number: p for p in pages}
    last_page_number = pages[-1].page_number if pages else 0

    chunks: List[PdfChunk] = []
    for i, entry in enumerate(ordered_entries):
        start = entry.page_number
        end = ordered_entries[i + 1].page_number - 1 if i + 1 < len(ordered_entries) else last_page_number
        end = max(end, start)  # guard against out-of-order/duplicate TOC page numbers

        chunk_pages = [n for n in range(start, end + 1) if n in pages_by_number]
        if not chunk_pages:
            continue

        text = "\n\n".join(pages_by_number[n].text for n in chunk_pages if pages_by_number[n].text)
        chunks.append(
            PdfChunk(chunk_id=f"chunk_{len(chunks) + 1}", heading=entry.title, pages=chunk_pages, text=text)
        )
    return chunks


def _chunk_by_window(pages: List[PdfPage]) -> List[PdfChunk]:
    max_chars = get_settings().PDF_CHUNK_MAX_CHARS

    chunks: List[PdfChunk] = []
    current_pages: List[int] = []
    current_texts: List[str] = []
    current_len = 0

    def flush() -> None:
        if not current_pages:
            return
        chunks.append(
            PdfChunk(
                chunk_id=f"chunk_{len(chunks) + 1}",
                heading=None,
                pages=list(current_pages),
                text="\n\n".join(t for t in current_texts if t),
            )
        )

    for page in pages:
        page_len = len(page.text)
        # Only split *between* pages, never mid-page -- a page that alone
        # exceeds the budget still gets its own chunk rather than being cut.
        if current_pages and current_len + page_len > max_chars:
            flush()
            current_pages, current_texts, current_len = [], [], 0

        current_pages.append(page.page_number)
        current_texts.append(page.text)
        current_len += page_len

    flush()
    return chunks
