"""
PDF Validation & Text Extraction.

Validates an uploaded PDF (openable, not password-protected, has at least
one page, under the size limit), then extracts per-page text via PyMuPDF,
building the intermediate PdfDocument representation. Pages with little or
no extractable text fall back to OCR.

Maps to doc/pdf-extraction.md Stages 1-3 (validation, metadata, text
extraction) and Stage 5 (OCR fallback).
"""

import logging

import pymupdf

from src.app.core.config import get_settings
from src.app.schemas.pdf import ExtractionMethod, PdfDocument, PdfMetadata, PdfPage, PdfTocEntry

logger = logging.getLogger("PdfExtractor")


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be validated or its text extracted.

    Carries a `stage`/`code` pair (rather than just a message) so the API
    layer can produce the stage-tagged error responses described in
    doc/pdf-extraction.md Stage 22, e.g.
    {"stage": "validation", "error": {"code": "ENCRYPTED_PDF", ...}}.
    """

    def __init__(self, message: str, *, stage: str, code: str, status_code: int = 422):
        super().__init__(message)
        self.stage = stage
        self.code = code
        self.status_code = status_code


def _open_and_validate(file_bytes: bytes) -> pymupdf.Document:
    """Opens the uploaded bytes as a PDF, raising PdfExtractionError for anything unusable."""
    if not file_bytes:
        raise PdfExtractionError(
            "The uploaded file was empty.", stage="validation", code="EMPTY_FILE"
        )

    settings = get_settings()
    if len(file_bytes) > settings.PDF_MAX_SIZE_BYTES:
        limit_mb = settings.PDF_MAX_SIZE_BYTES // (1024 * 1024)
        raise PdfExtractionError(
            f"The PDF exceeds the {limit_mb}MB size limit.",
            stage="validation",
            code="FILE_TOO_LARGE",
        )

    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise PdfExtractionError(
            "The uploaded file could not be processed as a PDF.",
            stage="validation",
            code="INVALID_PDF",
        ) from e

    # `is_encrypted` is also true for owner-password-only (permissions) PDFs,
    # which are fully readable without a password -- `needs_pass` is the
    # correct check for "we cannot open this without a password".
    if doc.needs_pass:
        doc.close()
        raise PdfExtractionError(
            "The PDF is password-protected and cannot be processed.",
            stage="validation",
            code="ENCRYPTED_PDF",
        )

    if doc.page_count == 0:
        doc.close()
        raise PdfExtractionError(
            "The PDF contains no pages.", stage="validation", code="EMPTY_PDF"
        )

    return doc


def _extract_metadata(doc: pymupdf.Document) -> PdfMetadata:
    raw = doc.metadata or {}
    toc = [
        PdfTocEntry(level=level, title=title, page_number=page_number)
        for level, title, page_number in doc.get_toc()
    ]
    return PdfMetadata(
        title=raw.get("title") or None,
        author=raw.get("author") or None,
        subject=raw.get("subject") or None,
        keywords=raw.get("keywords") or None,
        page_count=doc.page_count,
        creation_date=raw.get("creationDate") or None,
        modification_date=raw.get("modDate") or None,
        toc=toc,
    )


def _ocr_page(page: pymupdf.Page) -> str:
    """Runs OCR on a single page via PyMuPDF's Tesseract integration.

    Requires a system Tesseract install with tessdata available (see the
    backend README). Isolated into its own function so it can be mocked in
    tests without a real OCR engine installed.
    """
    ocr_textpage = page.get_textpage_ocr(full=False)
    return page.get_text("text", textpage=ocr_textpage, sort=True)


def _extract_page_text(page: pymupdf.Page) -> tuple[str, ExtractionMethod]:
    """Extracts a page's text, falling back to OCR when normal extraction is too sparse.

    OCR is only attempted for pages that need it -- it is significantly
    slower than normal text extraction and should not run on every page.
    A failed OCR attempt (e.g. no Tesseract installed) does not abort the
    whole document; it's recorded as "ocr_failed" so the rest of the PDF
    can still be processed.
    """
    text = page.get_text("text", sort=True).strip()

    settings = get_settings()
    if not settings.PDF_OCR_ENABLED or len(text) >= settings.PDF_MIN_TEXT_CHARS_PER_PAGE:
        return text, "text"

    try:
        ocr_text = _ocr_page(page).strip()
    except Exception as e:
        logger.warning(f"OCR failed for page {page.number + 1}: {e}")
        return text, "ocr_failed"

    return (ocr_text, "ocr") if ocr_text else (text, "text")


def extract_pdf(file_bytes: bytes) -> PdfDocument:
    """Validates the uploaded bytes as a PDF and extracts its text, page by page.

    Raises PdfExtractionError for anything that makes the file unusable as a
    whole (bad format, password-protected, empty, oversized). Per-page OCR
    failures are recorded on the page itself rather than aborting extraction.
    """
    doc = _open_and_validate(file_bytes)
    try:
        metadata = _extract_metadata(doc)
        pages = []
        for page in doc:
            text, method = _extract_page_text(page)
            pages.append(PdfPage(page_number=page.number + 1, text=text, extraction_method=method))
        return PdfDocument(metadata=metadata, pages=pages)
    finally:
        doc.close()
