"""
AI Topic Organization Service.
Uses the LLM Gateway to propose a learning order for a preparation's topics
based on prerequisites, dependencies, and conceptual progression, and to
group topics into logical sections where it makes sense.

Scope is strictly limited to producing an ordering and section grouping —
no free-form chat, no explanations beyond a short one-sentence rationale,
no open-ended interaction. This service never applies anything itself;
the caller decides how/when to apply the suggestion.
"""

import logging
from typing import List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from src.app.schemas.topics import (
    OrganizeSectionItem,
    OrganizeTopicItem,
    TopicOrganizeResponse,
    TopicSectionAssignment,
)
from src.app.services.chat_service import gateway
from src.app.services.llm_json import extract_json_object

logger = logging.getLogger("TopicOrganizerService")

SYSTEM_PROMPT = (
    "You are a learning-path planner. Given a numbered list of topics for a "
    "preparation (and optionally a list of existing sections), do two things:\n\n"
    "1. ORDER: Determine the most sensible overall learning order based on "
    "prerequisites, dependencies, and conceptual progression -- so a learner "
    "never has to tackle an advanced or dependent topic before its foundation.\n\n"
    "2. GROUP: Assign each topic to a logical section (e.g. 'Frontend', "
    "'Backend', 'Database'). Reuse an existing section name exactly (same "
    "spelling/case) when a topic clearly fits it. Otherwise invent a short, "
    "clear new section name. Only leave a topic ungrouped (null) if forcing "
    "it into a section would be meaningless -- prefer grouping when there are "
    "3 or more topics.\n\n"
    "Respond with ONLY a JSON object of this exact shape:\n"
    '{"order": [<index>, <index>, ...], '
    '"topic_sections": [<section name or null>, <section name or null>, ...], '
    '"reasoning": "<one short sentence>"}\n\n'
    'The "order" array MUST be a permutation of every input index (0-based), '
    "the same length as the input, each index appearing exactly once.\n"
    'The "topic_sections" array MUST have exactly one entry per input topic, '
    "in INPUT order (index i of this array describes input topic i, "
    "regardless of the order array). "
    "Do not include any text outside the JSON object."
)


class TopicOrganizerError(Exception):
    """Raised when the AI cannot produce a valid topic ordering."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _build_user_prompt(
    preparation_title: str,
    preparation_type: Optional[str],
    topics: List[OrganizeTopicItem],
    sections: List[OrganizeSectionItem],
) -> str:
    numbered = "\n".join(f"{i}. {t.name}" for i, t in enumerate(topics))
    context = f'Preparation: "{preparation_title}"'
    if preparation_type:
        context += f" ({preparation_type})"

    section_block = ""
    if sections:
        section_names = ", ".join(f'"{s.name}"' for s in sections)
        section_block = f"\n\nExisting sections (reuse these names when a topic fits): {section_names}"

    return f"{context}\n\nTopics:\n{numbered}{section_block}"


def _parse_response(
    raw_reply: str, expected_length: int
) -> Tuple[List[int], List[Optional[str]], Optional[str]]:
    """Parses and validates the AI's ordering and section grouping."""
    try:
        payload = extract_json_object(raw_reply)
    except ValueError as e:
        raise TopicOrganizerError(str(e))
    order = payload.get("order")
    reasoning = payload.get("reasoning")

    if not isinstance(order, list) or len(order) != expected_length:
        raise TopicOrganizerError("AI response did not return a complete ordering.")

    try:
        normalized_order = [int(i) for i in order]
    except (TypeError, ValueError):
        raise TopicOrganizerError("AI response order contained non-integer entries.")

    if sorted(normalized_order) != list(range(expected_length)):
        raise TopicOrganizerError("AI response order was not a valid permutation of the topics.")

    # Section grouping is a best-effort addition — fall back to "ungrouped"
    # for every topic rather than failing the whole (already-valid) ordering.
    topic_sections = payload.get("topic_sections")
    if not isinstance(topic_sections, list) or len(topic_sections) != expected_length:
        topic_sections = [None] * expected_length
    else:
        topic_sections = [
            s.strip() if isinstance(s, str) and s.strip() else None for s in topic_sections
        ]

    return normalized_order, topic_sections, reasoning if isinstance(reasoning, str) else None


class TopicOrganizerService:
    """Proposes an AI-assisted learning order and section grouping for a preparation's topics."""

    def __init__(self, gateway_instance=gateway):
        self.gateway = gateway_instance

    async def organize(
        self,
        preparation_title: str,
        preparation_type: Optional[str],
        topics: List[OrganizeTopicItem],
        sections: Optional[List[OrganizeSectionItem]] = None,
    ) -> TopicOrganizeResponse:
        if len(topics) < 2:
            raise TopicOrganizerError(
                "At least two topics are required to suggest an order.", status_code=422
            )

        sections = sections or []
        user_prompt = _build_user_prompt(preparation_title, preparation_type, topics, sections)
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

        try:
            reply, provider_name, model_name, _usage, _events = await self.gateway.generate(
                messages=messages,
                temperature=0.2,
                max_tokens=800,
            )
        except Exception as e:
            logger.error(f"❌ Topic organization LLM call failed: {e}")
            raise TopicOrganizerError(f"AI ordering failed: {e}", status_code=502)

        order_indices, topic_section_names, reasoning = _parse_response(
            reply, expected_length=len(topics)
        )
        ordered_ids = [topics[i].id for i in order_indices]
        section_assignments = [
            TopicSectionAssignment(topic_id=topics[i].id, section_name=topic_section_names[i])
            for i in range(len(topics))
        ]

        logger.info(
            f"✨ AI topic order suggested for \"{preparation_title}\" via {provider_name} ({model_name})."
        )

        return TopicOrganizeResponse(
            ordered_topic_ids=ordered_ids,
            section_assignments=section_assignments,
            reasoning=reasoning,
            provider=provider_name,
            model=model_name,
        )


# Singleton instance
topic_organizer_service = TopicOrganizerService()
