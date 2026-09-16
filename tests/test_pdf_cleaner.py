"""
Unit tests for PDF content cleaning (repeated headers/footers, page
numbers, excess blank lines).
"""

from typing import List, Optional

from src.app.schemas.pdf import PdfDocument, PdfMetadata, PdfPage, PdfTocEntry
from src.app.services.pdf.cleaner import clean_document


def _page(number: int, text: str) -> PdfPage:
    return PdfPage(page_number=number, text=text, extraction_method="text")


def _document(pages: List[PdfPage], toc: Optional[List[PdfTocEntry]] = None) -> PdfDocument:
    return PdfDocument(metadata=PdfMetadata(page_count=len(pages), toc=toc or []), pages=pages)


def test_strips_repeated_header_and_footer_and_page_numbers():
    pages = [
        _page(1, "ToPrep Study Guide\n\nReact is a JavaScript library for building UIs.\n\nPage 1\nConfidential"),
        _page(2, "ToPrep Study Guide\n\nHooks let function components use state.\n\nPage 2\nConfidential"),
        _page(3, "ToPrep Study Guide\n\nuseEffect handles side effects.\n\nPage 3\nConfidential"),
    ]

    cleaned = clean_document(_document(pages))

    for page in cleaned.pages:
        assert "ToPrep Study Guide" not in page.text
        assert "Confidential" not in page.text
        assert "Page " not in page.text

    assert "React is a JavaScript library for building UIs." in cleaned.pages[0].text
    assert "Hooks let function components use state." in cleaned.pages[1].text
    assert "useEffect handles side effects." in cleaned.pages[2].text


def test_preserves_heading_that_only_appears_once():
    pages = [
        _page(1, "CHAPTER 4\n\nReact\n\nReact is a JavaScript library..."),
        _page(2, "Components let you split the UI into independent pieces."),
        _page(3, "Props are read-only inputs to components."),
    ]

    cleaned = clean_document(_document(pages))

    assert "CHAPTER 4" in cleaned.pages[0].text
    assert "React is a JavaScript library" in cleaned.pages[0].text


def test_removes_standalone_page_number_variants():
    pages = [
        _page(1, "Intro content.\n\n24"),
        _page(2, "More content.\n\nPage 25"),
        _page(3, "Even more content.\n\n3 of 10"),
    ]

    cleaned = clean_document(_document(pages))

    assert cleaned.pages[0].text == "Intro content."
    assert cleaned.pages[1].text == "More content."
    assert cleaned.pages[2].text == "Even more content."


def test_collapses_excess_blank_lines():
    text = "First paragraph.\n\n\n\n\nSecond paragraph."

    cleaned = clean_document(_document([_page(1, text), _page(2, "filler"), _page(3, "filler")]))

    assert cleaned.pages[0].text == "First paragraph.\n\nSecond paragraph."


def test_skips_repeat_detection_below_minimum_page_count():
    # Only two pages -- a coincidentally shared first line should NOT be
    # treated as a repeated header (too little evidence).
    pages = [
        _page(1, "Overview\n\nThis is the first page of a short two-page handout."),
        _page(2, "Overview\n\nThis is the second page of the same handout."),
    ]

    cleaned = clean_document(_document(pages))

    assert "Overview" in cleaned.pages[0].text
    assert "Overview" in cleaned.pages[1].text
