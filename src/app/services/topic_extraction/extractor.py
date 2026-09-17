"""
LLM Topic Extraction.

Runs each PDF chunk through the shared LLM gateway (chat_service.gateway --
the same multi-provider, automatic-failover gateway used by chat and topic
organization) to extract candidate learning topics, following the same
system/human message + tolerant JSON parsing + typed-error pattern as
topic_organizer_service.py.

Maps to doc/pdf-extraction.md Stages 10, 13-15.
"""

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.app.schemas.pdf import ExtractedTopic, PdfChunk
from src.app.services.chat_service import gateway
from src.app.services.llm_json import extract_json_object
from src.app.services.topic_extraction.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_user_prompt,
)

logger = logging.getLogger("PdfTopicExtractor")


class TopicExtractionError(Exception):
    """Raised when the LLM cannot produce a valid topic list for a chunk."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _parse_topic_names(raw_reply: str) -> List[str]:
    try:
        payload = extract_json_object(raw_reply)
    except ValueError as e:
        raise TopicExtractionError(f"AI response was not valid JSON: {e}")

    topics = payload.get("topics")
    if not isinstance(topics, list):
        raise TopicExtractionError("AI response did not contain a 'topics' array.")

    return [t.strip() for t in topics if isinstance(t, str) and t.strip()]


async def extract_topics_from_chunk(chunk: PdfChunk, gateway_instance=gateway) -> List[ExtractedTopic]:
    """Extracts candidate learning topics from a single PDF chunk via the LLM gateway."""
    if not chunk.text.strip():
        return []

    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=build_extraction_user_prompt(chunk)),
    ]

    try:
        reply, provider_name, model_name, _usage, _events = await gateway_instance.generate(
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )
    except Exception as e:
        logger.error(f"❌ Topic extraction LLM call failed for {chunk.chunk_id}: {e}")
        raise TopicExtractionError(f"Topic extraction failed: {e}")

    names = _parse_topic_names(reply)
    logger.info(
        f"✨ Extracted {len(names)} candidate topic(s) from {chunk.chunk_id} via {provider_name} ({model_name})."
    )
    return [ExtractedTopic(name=name, source_pages=chunk.pages, chunk_ids=[chunk.chunk_id]) for name in names]


async def extract_topics(chunks: List[PdfChunk], gateway_instance=gateway) -> List[ExtractedTopic]:
    """Extracts topics from every chunk and aggregates them into one flat list.

    Chunks are processed sequentially and a chunk's failure aborts the whole
    extraction (rather than silently dropping its topics) -- the gateway
    already retries across every configured provider before raising, so a
    failure here means the document genuinely couldn't be processed.
    """
    all_topics: List[ExtractedTopic] = []
    for chunk in chunks:
        all_topics.extend(await extract_topics_from_chunk(chunk, gateway_instance))
    return all_topics
