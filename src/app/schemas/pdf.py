"""
Pydantic Schemas for PDF Ingestion.

Houses the intermediate PdfPage/PdfDocument representation used between
PDF extraction and topic extraction (see doc/pdf-extraction.md Stage 6).
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ExtractionMethod = Literal["text", "ocr", "ocr_failed"]


class PdfTocEntry(BaseModel):
    """One entry from the PDF's table of contents / bookmarks (PyMuPDF get_toc())."""
    level: int = Field(..., description="Nesting level, 1 = top-level")
    title: str = Field(..., description="Bookmark title")
    page_number: int = Field(..., description="1-indexed page this entry points to")


class PdfMetadata(BaseModel):
    """Document-level metadata. Supporting information only, not a source of topics."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    page_count: int = Field(..., description="Total number of pages in the document")
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    toc: List[PdfTocEntry] = Field(
        default_factory=list, description="Table of contents / bookmarks, if present"
    )


class PdfPage(BaseModel):
    """A single extracted page, with provenance of how its text was obtained."""
    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Extracted page text")
    extraction_method: ExtractionMethod = Field(
        ...,
        description=(
            "How this page's text was obtained: normal extraction, OCR, or a "
            "failed OCR attempt (text may be empty/sparse in that case)."
        ),
    )


class PdfDocument(BaseModel):
    """Intermediate representation between PDF extraction and topic extraction."""
    metadata: PdfMetadata
    pages: List[PdfPage]
