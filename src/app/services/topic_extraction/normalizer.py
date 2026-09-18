"""
Topic Normalization & Deduplication.

Merges naming variants of the same concept extracted from different PDF
chunks (e.g. "React Hooks" / "Hooks in React") into a single canonical
topic via a second pass through the shared LLM gateway, without merging
related-but-distinct concepts.

Maps to doc/pdf-extraction.md Stages 16-17.
"""

import logging
from typing import List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from src.app.schemas.pdf import ExtractedTopic
from src.app.services.chat_service import gateway
from src.app.services.llm_json import extract_json_object
from src.app.services.topic_extraction.prompts import (
    NORMALIZATION_SYSTEM_PROMPT,
    build_normalization_user_prompt,
)

logger = logging.getLogger("PdfTopicNormalizer")


class TopicNormalizationError(Exception):
    """Raised when the LLM cannot produce a valid grouping of the extracted topics."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _validate_groups(groups_raw: list, expected_length: int) -> List[Tuple[str, List[int]]]:
    """Validates the AI's duplicate-merge groups.

    Unlike a full partition, an index is allowed to appear in *no* group --
    that's how the model reports "this topic has no duplicate" (see
    NORMALIZATION_SYSTEM_PROMPT). It just can't appear in more than one.
    """
    seen = set()
    groups: List[Tuple[str, List[int]]] = []

    for group in groups_raw:
        if not isinstance(group, dict):
            raise TopicNormalizationError("AI response contained a malformed group.")
        name = group.get("name")
        indices = group.get("indices")
        if not isinstance(name, str) or not name.strip():
            raise TopicNormalizationError("A group was missing a valid name.")
        if not isinstance(indices, list) or not indices:
            raise TopicNormalizationError(f"Group '{name}' had no indices.")

        try:
            int_indices = [int(i) for i in indices]
        except (TypeError, ValueError):
            raise TopicNormalizationError(f"Group '{name}' had non-integer indices.")

        for i in int_indices:
            if i < 0 or i >= expected_length:
                raise TopicNormalizationError(f"Group '{name}' referenced an out-of-range index {i}.")
            if i in seen:
                raise TopicNormalizationError(f"Index {i} was assigned to more than one group.")
            seen.add(i)

        groups.append((name.strip(), int_indices))

    return groups


async def normalize_and_deduplicate(
    topics: List[ExtractedTopic], gateway_instance=gateway
) -> List[ExtractedTopic]:
    """Merges naming variants / duplicate topics into one canonical entry per concept.

    A single topic (or none) has nothing to deduplicate against, so the
    LLM pass is skipped in that case.
    """
    if len(topics) < 2:
        return topics

    messages = [
        SystemMessage(content=NORMALIZATION_SYSTEM_PROMPT),
        HumanMessage(content=build_normalization_user_prompt([t.name for t in topics])),
    ]

    try:
        reply, provider_name, model_name, _usage, _events = await gateway_instance.generate(
            messages=messages,
            temperature=0.1,
            max_tokens=8000,
        )
    except Exception as e:
        logger.error(f"❌ Topic normalization LLM call failed: {e}")
        raise TopicNormalizationError(f"Topic normalization failed: {e}")

    try:
        payload = extract_json_object(reply)
    except ValueError as e:
        raise TopicNormalizationError(f"AI response was not valid JSON: {e}")

    groups_raw = payload.get("groups")
    if not isinstance(groups_raw, list):
        raise TopicNormalizationError("AI response did not contain a 'groups' array.")

    groups = _validate_groups(groups_raw, expected_length=len(topics))

    merged: List[ExtractedTopic] = []
    grouped_indices: set = set()
    for name, indices in groups:
        grouped_indices.update(indices)
        pages = sorted({p for i in indices for p in topics[i].source_pages})
        chunk_ids = sorted({c for i in indices for c in topics[i].chunk_ids})
        merged.append(ExtractedTopic(name=name, source_pages=pages, chunk_ids=chunk_ids))

    # Any index the AI didn't mention has no duplicate -- keep it as-is.
    for i, topic in enumerate(topics):
        if i not in grouped_indices:
            merged.append(topic)

    logger.info(
        f"✨ Normalized {len(topics)} raw topic(s) into {len(merged)} via {provider_name} ({model_name})."
    )
    return merged
