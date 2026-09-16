"""
Unit tests for PDF validation, text extraction, and OCR fallback.
No real Tesseract/OCR engine required -- the OCR call is mocked.
"""

from typing import List, Optional
from unittest.mock import MagicMock, patch

import pymupdf
import pytest

from src.app.core.config import get_settings
from src.app.services.pdf.extractor import PdfExtractionError, extract_pdf


def _build_pdf(page_texts: List[Optional[str]]) -> bytes:
    """Builds an in-memory PDF with one page per entry (empty page if text is None)."""
    doc = pymupdf.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _build_encrypted_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Secret content that needs a password to read.")
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")
    doc.close()
    return data


def test_extracts_text_from_normal_pdf():
    pdf_bytes = _build_pdf(["First page of real content.", "Second page of real content."])

    document = extract_pdf(pdf_bytes)

    assert document.metadata.page_count == 2
    assert [p.page_number for p in document.pages] == [1, 2]
    assert document.pages[0].extraction_method == "text"
    assert "First page" in document.pages[0].text
    assert "Second page" in document.pages[1].text


def test_extracts_toc_when_present():
    pdf_bytes = _build_pdf(["Chapter one content.", "Chapter two content."])
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    doc.set_toc([[1, "Chapter One", 1], [1, "Chapter Two", 2]])
    pdf_bytes = doc.tobytes()
    doc.close()

    document = extract_pdf(pdf_bytes)

    assert [entry.title for entry in document.metadata.toc] == ["Chapter One", "Chapter Two"]


def test_rejects_empty_file():
    with pytest.raises(PdfExtractionError) as exc_info:
        extract_pdf(b"")
    assert exc_info.value.stage == "validation"
    assert exc_info.value.code == "EMPTY_FILE"


def test_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(get_settings(), "PDF_MAX_SIZE_BYTES", 10)

    with pytest.raises(PdfExtractionError) as exc_info:
        extract_pdf(b"x" * 100)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_rejects_non_pdf_file():
    with pytest.raises(PdfExtractionError) as exc_info:
        extract_pdf(b"this is definitely not a pdf file, just text bytes")
    assert exc_info.value.code == "INVALID_PDF"


def test_rejects_encrypted_pdf():
    with pytest.raises(PdfExtractionError) as exc_info:
        extract_pdf(_build_encrypted_pdf())
    assert exc_info.value.code == "ENCRYPTED_PDF"


def test_rejects_zero_page_pdf():
    fake_doc = MagicMock()
    fake_doc.needs_pass = False
    fake_doc.page_count = 0

    with patch("src.app.services.pdf.extractor.pymupdf.open", return_value=fake_doc):
        with pytest.raises(PdfExtractionError) as exc_info:
            extract_pdf(b"%PDF-1.7 fake but non-empty bytes")

    assert exc_info.value.code == "EMPTY_PDF"
    fake_doc.close.assert_called_once()


def test_normal_text_pdf_does_not_invoke_ocr():
    pdf_bytes = _build_pdf(["Plenty of real extractable text on this page, no OCR needed."])

    with patch("src.app.services.pdf.extractor._ocr_page") as mock_ocr:
        document = extract_pdf(pdf_bytes)

    mock_ocr.assert_not_called()
    assert document.pages[0].extraction_method == "text"


def test_sparse_page_falls_back_to_ocr():
    pdf_bytes = _build_pdf([None])  # blank page -> no extractable text

    with patch(
        "src.app.services.pdf.extractor._ocr_page",
        return_value="Text recovered via OCR from a scanned page.",
    ) as mock_ocr:
        document = extract_pdf(pdf_bytes)

    mock_ocr.assert_called_once()
    assert document.pages[0].extraction_method == "ocr"
    assert document.pages[0].text == "Text recovered via OCR from a scanned page."


def test_ocr_failure_does_not_abort_extraction():
    pdf_bytes = _build_pdf([None])

    with patch(
        "src.app.services.pdf.extractor._ocr_page",
        side_effect=RuntimeError("Tesseract not installed"),
    ):
        document = extract_pdf(pdf_bytes)

    assert document.pages[0].extraction_method == "ocr_failed"
    assert document.pages[0].text == ""


def test_ocr_disabled_skips_fallback_entirely(monkeypatch):
    monkeypatch.setattr(get_settings(), "PDF_OCR_ENABLED", False)
    pdf_bytes = _build_pdf([None])

    with patch("src.app.services.pdf.extractor._ocr_page") as mock_ocr:
        document = extract_pdf(pdf_bytes)

    mock_ocr.assert_not_called()
    assert document.pages[0].extraction_method == "text"
