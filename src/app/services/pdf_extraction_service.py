"""
PDF-to-Topics Extraction Pipeline.

Orchestrates the full pipeline: validation & text extraction -> cleaning ->
chunking -> LLM topic extraction -> normalization/dedup. Thin glue only --
each stage's actual logic lives in services/pdf/* and
services/topic_extraction/*. See doc/pdf-extraction-phases.md.

Runs as an async generator so the API layer can stream stage-by-stage
progress to the client instead of leaving it staring at a spinner for
however long the LLM calls take.
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from src.app.schemas.pdf import ExtractedTopic
from src.app.schemas.topics import OrganizeTopicItem
from src.app.services.pdf.chunker import chunk_document
from src.app.services.pdf.cleaner import clean_document
from src.app.services.pdf.extractor import PdfExtractionError, extract_pdf
from src.app.services.topic_extraction.extractor import (
    TopicExtractionError,
    extract_topics_from_chunk,
)
from src.app.services.topic_extraction.normalizer import (
    TopicNormalizationError,
    normalize_and_deduplicate,
)
from src.app.services.topic_organizer_service import topic_organizer_service

logger = logging.getLogger("PdfExtractionService")


def _event(stage: str, event_status: str, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"stage": stage, "status": event_status}
    payload.update(extra)
    return payload


async def _group_into_sections(
    topics: List[ExtractedTopic], document_title: Optional[str]
) -> List[Dict[str, Optional[str]]]:
    """Runs the deduplicated topic list through the same AI organizer used by
    the "Organize with AI" button, so a PDF that's already structured into
    sections (a syllabus, a roadmap) comes in pre-sorted into matching
    sections instead of landing as one flat, ungrouped list.

    Best-effort: this is a bonus pass over topics that were already
    successfully extracted, so a failure here falls back to the topics in
    their original order, ungrouped, rather than discarding real work.
    """
    if len(topics) < 2:
        return [{"name": t.name, "section": None} for t in topics]

    items = [OrganizeTopicItem(id=f"t{i}", name=t.name) for i, t in enumerate(topics)]
    try:
        result = await topic_organizer_service.organize(
            preparation_title=document_title or "this document",
            preparation_type=None,
            topics=items,
        )
    except Exception as e:
        logger.warning(f"⚠️ Section grouping skipped, falling back to a flat list: {e}")
        return [{"name": t.name, "section": None} for t in topics]

    name_by_id = {item.id: item.name for item in items}
    section_by_id = {a.topic_id: a.section_name for a in result.section_assignments}
    return [
        {"name": name_by_id[topic_id], "section": section_by_id.get(topic_id)}
        for topic_id in result.ordered_topic_ids
    ]


async def stream_topics_from_pdf(file_bytes: bytes) -> AsyncIterator[Dict[str, Any]]:
    """Runs the PDF -> topics pipeline, yielding progress events as it goes.

    Every event has a `stage` ("validating" | "reading" | "analyzing" |
    "organizing" | "grouping" | "complete" | "error") and a `status`
    ("active" | "done" | "error"). The stream always ends in exactly one of:
      - {"stage": "complete", "status": "done",
         "topics": [{"name": str, "section": str | None}, ...]}
      - {"stage": "error", "status": "error", "message": "...", "status_code": <int>}

    Domain errors (bad PDF, AI response the pipeline couldn't use) are caught
    here and turned into that final error event rather than raised, since by
    the time they happen the HTTP response has already started streaming a
    200 -- the status code travels inside the event instead.
    """
    try:
        yield _event("validating", "active", message="Validating your PDF…")
        yield _event("validating", "done")

        yield _event("reading", "active", message="Reading the document…")
        document = extract_pdf(file_bytes)
        cleaned = clean_document(document)
        chunks = chunk_document(cleaned)
        yield _event(
            "reading",
            "done",
            message=(
                f"Read {document.metadata.page_count} page"
                f"{'' if document.metadata.page_count == 1 else 's'}"
            ),
        )

        raw_topics: List[ExtractedTopic] = []
        total_chunks = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            yield _event(
                "analyzing",
                "active",
                message=f"AI is reading section {index} of {total_chunks}…",
                current=index,
                total=total_chunks,
            )
            raw_topics.extend(await extract_topics_from_chunk(chunk))
        yield _event(
            "analyzing",
            "done",
            message=f"Found {len(raw_topics)} candidate topic{'' if len(raw_topics) == 1 else 's'}",
        )

        yield _event("organizing", "active", message="Grouping duplicate topics…")
        deduped_topics = await normalize_and_deduplicate(raw_topics)
        yield _event("organizing", "done")

        yield _event("grouping", "active", message="Sorting topics into sections…")
        sectioned_topics = await _group_into_sections(deduped_topics, document.metadata.title)
        yield _event("grouping", "done")

        logger.info(
            f"✅ Extracted {len(deduped_topics)} topic(s) from a {document.metadata.page_count}-page PDF "
            f"({len(chunks)} chunk(s))."
        )
        yield _event("complete", "done", topics=sectioned_topics)

    except (PdfExtractionError, TopicExtractionError, TopicNormalizationError) as e:
        yield _event("error", "error", message=str(e), status_code=e.status_code)
    except Exception as e:
        logger.error(f"❌ PDF pipeline failed: {e}")
        yield _event(
            "error",
            "error",
            message=f"PDF topic extraction failed: {e}",
            status_code=500,
        )
