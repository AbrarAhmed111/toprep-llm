"""
PDF-to-Topics Extraction Pipeline.

Orchestrates the full pipeline: validation & text extraction -> cleaning ->
chunking -> LLM topic extraction -> normalization/dedup. Thin glue only --
each stage's actual logic lives in services/pdf/* and
services/topic_extraction/*. See doc/pdf-extraction-phases.md.
"""

import logging
from typing import List

from src.app.services.pdf.chunker import chunk_document
from src.app.services.pdf.cleaner import clean_document
from src.app.services.pdf.extractor import extract_pdf
from src.app.services.topic_extraction.extractor import extract_topics
from src.app.services.topic_extraction.normalizer import normalize_and_deduplicate

logger = logging.getLogger("PdfExtractionService")


async def extract_topics_from_pdf(file_bytes: bytes) -> List[str]:
    """Runs the full PDF -> topics pipeline, returning a flat deduplicated topic-name list.

    Propagates PdfExtractionError (validation/extraction), TopicExtractionError,
    or TopicNormalizationError from whichever stage fails -- the API layer
    maps these to user-readable HTTP responses.
    """
    document = extract_pdf(file_bytes)
    cleaned = clean_document(document)
    chunks = chunk_document(cleaned)

    raw_topics = await extract_topics(chunks)
    deduped_topics = await normalize_and_deduplicate(raw_topics)

    logger.info(
        f"✅ Extracted {len(deduped_topics)} topic(s) from a {document.metadata.page_count}-page PDF "
        f"({len(chunks)} chunk(s))."
    )
    return [t.name for t in deduped_topics]
