"""
PDF Content Cleaning.

Strips extraction noise (repeated headers/footers, standalone page-number
lines, excess whitespace) from an extracted PdfDocument, conservatively,
without altering its meaning or structure.

Maps to doc/pdf-extraction.md Stage 7.
"""

import re
from typing import List, Set

from src.app.schemas.pdf import PdfDocument, PdfPage

# Matches a line that is *only* a page number, optionally with a "page"/"of"
# label -- e.g. "24", "Page 24", "3 of 10", "page 3/10".
_PAGE_NUMBER_LINE = re.compile(r"^(page\s+)?\d+(\s*(of|/)\s*\d+)?$", re.IGNORECASE)

# How many lines from the top/bottom of a page count as header/footer candidates.
_EDGE_LINES_CHECKED = 2

# A repeated header/footer needs at least this many pages to distinguish it
# from a heading that coincidentally matches on a couple of short pages.
_MIN_PAGES_FOR_REPEAT_DETECTION = 3

# Fraction of pages a candidate line must appear on (as an edge line) to be
# treated as a repeated header/footer rather than real content.
_REPEAT_RATIO_THRESHOLD = 0.6


def clean_document(document: PdfDocument) -> PdfDocument:
    """Returns a copy of `document` with repeated headers/footers, standalone
    page-number lines, and excess blank lines stripped from every page."""
    noise_lines = _find_repeated_edge_lines(document.pages, from_end=False) | _find_repeated_edge_lines(
        document.pages, from_end=True
    )

    cleaned_pages = [
        page.model_copy(update={"text": _clean_page_text(page.text, noise_lines)}) for page in document.pages
    ]
    return document.model_copy(update={"pages": cleaned_pages})


def _edge_lines(text: str, from_end: bool) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    return lines[-_EDGE_LINES_CHECKED:] if from_end else lines[:_EDGE_LINES_CHECKED]


def _find_repeated_edge_lines(pages: List[PdfPage], from_end: bool) -> Set[str]:
    """Finds lines that recur as a header/footer candidate across most pages.

    Page-number lines are excluded here since they differ per page (and are
    stripped unconditionally in `_clean_page_text` instead).
    """
    if len(pages) < _MIN_PAGES_FOR_REPEAT_DETECTION:
        return set()

    counts: dict = {}
    for page in pages:
        for line in set(_edge_lines(page.text, from_end)):
            if not _PAGE_NUMBER_LINE.match(line):
                counts[line] = counts.get(line, 0) + 1

    threshold = max(2, round(len(pages) * _REPEAT_RATIO_THRESHOLD))
    return {line for line, count in counts.items() if count >= threshold}


def _clean_page_text(text: str, noise_lines: Set[str]) -> str:
    kept_lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and (line in noise_lines or _PAGE_NUMBER_LINE.match(line)):
            continue
        kept_lines.append(line)

    collapsed: List[str] = []
    for line in kept_lines:
        if line == "" and (not collapsed or collapsed[-1] == ""):
            continue
        collapsed.append(line)

    return "\n".join(collapsed).strip()
