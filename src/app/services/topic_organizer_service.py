"""
AI Topic Organization Service.
Uses the LLM Gateway to propose a learning order for a preparation's topics
based on prerequisites, dependencies, and conceptual progression.

Scope is strictly limited to producing an ordering — no free-form chat,
no explanations beyond a short one-sentence rationale, no open-ended
interaction. The caller (frontend) must always show the suggestion for
explicit user review and acceptance; nothing here applies changes silently.
"""

import json
import logging
from typing import List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from src.app.schemas.topics import OrganizeTopicItem, TopicOrganizeResponse
from src.app.services.chat_service import gateway

logger = logging.getLogger("TopicOrganizerService")

SYSTEM_PROMPT = (
    "You are a learning-path planner. Given a numbered list of topics for a "
    "preparation, determine the most sensible learning order based on "
    "prerequisites, dependencies, and conceptual progression -- so a learner "
    "never has to tackle an advanced or dependent topic before its "
    "foundation.\n\n"
    "Respond with ONLY a JSON object of this exact shape:\n"
    '{"order": [<index>, <index>, ...], "reasoning": "<one short sentence>"}\n\n'
    'The "order" array MUST be a permutation of every input index (0-based), '
    "the same length as the input, with each index appearing exactly once. "
    "Do not include any text outside the JSON object."
)


class TopicOrganizerError(Exception):
    """Raised when the AI cannot produce a valid topic ordering."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _build_user_prompt(
    preparation_title: str, preparation_type: Optional[str], topics: List[OrganizeTopicItem]
) -> str:
    numbered = "\n".join(f"{i}. {t.name}" for i, t in enumerate(topics))
    context = f'Preparation: "{preparation_title}"'
    if preparation_type:
        context += f" ({preparation_type})"
    return f"{context}\n\nTopics:\n{numbered}"


def _extract_json_object(raw_reply: str) -> dict:
    """Extracts the outermost {...} block from a reply, tolerating surrounding prose/fences."""
    start = raw_reply.find("{")
    end = raw_reply.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise TopicOrganizerError("AI response did not contain a JSON object.")
    try:
        return json.loads(raw_reply[start : end + 1])
    except json.JSONDecodeError as e:
        raise TopicOrganizerError(f"AI response was not valid JSON: {e}")


def _parse_order(raw_reply: str, expected_length: int) -> Tuple[List[int], Optional[str]]:
    """Parses and validates the AI's ordering as a true permutation of the input indices."""
    payload = _extract_json_object(raw_reply)
    order = payload.get("order")
    reasoning = payload.get("reasoning")

    if not isinstance(order, list) or len(order) != expected_length:
        raise TopicOrganizerError("AI response did not return a complete ordering.")

    try:
        normalized = [int(i) for i in order]
    except (TypeError, ValueError):
        raise TopicOrganizerError("AI response order contained non-integer entries.")

    if sorted(normalized) != list(range(expected_length)):
        raise TopicOrganizerError("AI response order was not a valid permutation of the topics.")

    return normalized, reasoning if isinstance(reasoning, str) else None


class TopicOrganizerService:
    """Proposes an AI-assisted learning order for a preparation's topics."""

    def __init__(self, gateway_instance=gateway):
        self.gateway = gateway_instance

    async def organize(
        self,
        preparation_title: str,
        preparation_type: Optional[str],
        topics: List[OrganizeTopicItem],
    ) -> TopicOrganizeResponse:
        if len(topics) < 2:
            raise TopicOrganizerError(
                "At least two topics are required to suggest an order.", status_code=422
            )

        user_prompt = _build_user_prompt(preparation_title, preparation_type, topics)
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

        try:
            reply, provider_name, model_name, _usage, _events = await self.gateway.generate(
                messages=messages,
                temperature=0.2,
                max_tokens=600,
            )
        except Exception as e:
            logger.error(f"❌ Topic organization LLM call failed: {e}")
            raise TopicOrganizerError(f"AI ordering failed: {e}", status_code=502)

        order_indices, reasoning = _parse_order(reply, expected_length=len(topics))
        ordered_ids = [topics[i].id for i in order_indices]

        logger.info(
            f"✨ AI topic order suggested for \"{preparation_title}\" via {provider_name} ({model_name})."
        )

        return TopicOrganizeResponse(
            ordered_topic_ids=ordered_ids,
            reasoning=reasoning,
            provider=provider_name,
            model=model_name,
        )


# Singleton instance
topic_organizer_service = TopicOrganizerService()
