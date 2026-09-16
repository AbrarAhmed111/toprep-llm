"""
PDF Validation & Text Extraction.

Validates an uploaded PDF (openable, not encrypted, has extractable
content, under the size/page-count limits) and extracts per-page text via
PyMuPDF, building the intermediate PdfDocument representation. Falls back
to OCR for pages with little/no extractable text.

Maps to doc/pdf-extraction.md Stages 1-3 and Stage 5 (OCR).
Implemented in Phase 2 (validation + text extraction) and Phase 3 (OCR).
"""
