"""
PDF Chunking.

Splits a cleaned PdfDocument into LLM-sized chunks, preferring the PDF's
own structure (table of contents / bookmarks) as chunk boundaries and
falling back to a windowed split when no usable structure is present.
Each chunk retains its source page numbers for later provenance.

Maps to doc/pdf-extraction.md Stages 8-9. Implemented in Phase 4.
"""
