"""
Unit tests for PDF chunking: TOC-aligned chunks when a table of contents
exists, and a windowed fallback when it doesn't.
"""

from typing import List, Optional
from unittest.mock import patch

from src.app.core.config import get_settings
from src.app.schemas.pdf import PdfDocument, PdfMetadata, PdfPage, PdfTocEntry
from src.app.services.pdf.chunker import chunk_document


def _page(number: int, text: str) -> PdfPage:
    return PdfPage(page_number=number, text=text, extraction_method="text")


def _document(pages: List[PdfPage], toc: Optional[List[PdfTocEntry]] = None) -> PdfDocument:
    return PdfDocument(metadata=PdfMetadata(page_count=len(pages), toc=toc or []), pages=pages)


def test_chunks_align_to_top_level_toc_chapters():
    pages = [_page(n, f"Content of page {n}.") for n in range(1, 5)]
    toc = [PdfTocEntry(level=1, title="JavaScript", page_number=1), PdfTocEntry(level=1, title="React", page_number=3)]

    chunks = chunk_document(_document(pages, toc))

    assert [c.heading for c in chunks] == ["JavaScript", "React"]
    assert [c.pages for c in chunks] == [[1, 2], [3, 4]]
    assert "Content of page 1." in chunks[0].text
    assert "Content of page 2." in chunks[0].text
    assert "Content of page 3." in chunks[1].text
    assert "Content of page 4." in chunks[1].text
    assert [c.chunk_id for c in chunks] == ["chunk_1", "chunk_2"]


def test_sub_level_toc_entries_do_not_fragment_chunks():
    pages = [_page(n, f"Content of page {n}.") for n in range(1, 5)]
    toc = [
        PdfTocEntry(level=1, title="JavaScript", page_number=1),
        PdfTocEntry(level=2, title="Closures", page_number=2),
        PdfTocEntry(level=1, title="React", page_number=3),
    ]

    chunks = chunk_document(_document(pages, toc))

    assert len(chunks) == 2
    assert chunks[0].pages == [1, 2]
    assert chunks[1].pages == [3, 4]


def test_falls_back_to_windowed_chunks_without_toc():
    pages = [_page(n, "word " * 100) for n in range(1, 6)]  # ~500 chars/page, no TOC

    with patch.object(get_settings(), "PDF_CHUNK_MAX_CHARS", 1200):
        chunks = chunk_document(_document(pages))

    assert len(chunks) > 1
    assert all(c.heading is None for c in chunks)

    # Every page appears in exactly one chunk, in order, with nothing dropped.
    all_pages = [p for c in chunks for p in c.pages]
    assert all_pages == [1, 2, 3, 4, 5]


def test_short_document_without_toc_produces_single_chunk():
    pages = [_page(1, "Short intro."), _page(2, "Short body.")]

    chunks = chunk_document(_document(pages))

    assert len(chunks) == 1
    assert chunks[0].pages == [1, 2]


def test_oversized_single_page_gets_its_own_chunk():
    huge_page = _page(1, "x" * 50000)
    small_page = _page(2, "small")

    with patch.object(get_settings(), "PDF_CHUNK_MAX_CHARS", 1000):
        chunks = chunk_document(_document([huge_page, small_page]))

    assert [c.pages for c in chunks] == [[1], [2]]
