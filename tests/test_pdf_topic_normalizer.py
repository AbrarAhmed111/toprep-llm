"""
Unit tests for LLM-based topic normalization & deduplication.
Completely mocked (zero real LLM calls / tokens consumed). Mocks are
applied to the shared `chat_service.gateway` singleton to confirm
normalization goes through the same multi-provider fallback gateway as
everything else, rather than a separate LLM client.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.app.schemas.pdf import ExtractedTopic
from src.app.services.chat_service import gateway
from src.app.services.topic_extraction.normalizer import (
    TopicNormalizationError,
    normalize_and_deduplicate,
)


def _topic(name: str, pages: list, chunk_id: str) -> ExtractedTopic:
    return ExtractedTopic(name=name, source_pages=pages, chunk_ids=[chunk_id])


@pytest.mark.asyncio
async def test_merges_naming_variants_of_the_same_concept():
    topics = [
        _topic("React Hooks", [5], "chunk_1"),
        _topic("Hooks in React", [12], "chunk_3"),
        _topic("React.js Hooks", [20], "chunk_5"),
    ]
    mock_reply = json.dumps({"groups": [{"name": "React Hooks", "indices": [0, 1, 2]}]})

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        result = await normalize_and_deduplicate(topics)

    assert len(result) == 1
    assert result[0].name == "React Hooks"
    assert result[0].source_pages == [5, 12, 20]
    assert sorted(result[0].chunk_ids) == ["chunk_1", "chunk_3", "chunk_5"]


@pytest.mark.asyncio
async def test_does_not_merge_related_but_distinct_concepts():
    topics = [
        _topic("React State", [3], "chunk_1"),
        _topic("Redux", [8], "chunk_2"),
    ]
    mock_reply = json.dumps(
        {
            "groups": [
                {"name": "React State", "indices": [0]},
                {"name": "Redux", "indices": [1]},
            ]
        }
    )

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        result = await normalize_and_deduplicate(topics)

    assert {t.name for t in result} == {"React State", "Redux"}
    assert len(result) == 2


@pytest.mark.asyncio
async def test_skips_llm_call_for_a_single_topic():
    topics = [_topic("Only Topic", [1], "chunk_1")]

    with patch.object(gateway, "generate", new=AsyncMock()) as mock_generate:
        result = await normalize_and_deduplicate(topics)

    mock_generate.assert_not_called()
    assert result == topics


@pytest.mark.asyncio
async def test_keeps_topics_with_no_duplicate_as_singletons():
    # The AI only reports actual duplicate groups; an omitted index (like 1
    # here) means "no duplicate" and must survive under its original name.
    topics = [_topic("A", [1], "chunk_1"), _topic("B", [2], "chunk_2")]
    mock_reply = json.dumps({"groups": [{"name": "A", "indices": [0]}]})

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        result = await normalize_and_deduplicate(topics)

    assert {t.name for t in result} == {"A", "B"}
    assert len(result) == 2


@pytest.mark.asyncio
async def test_empty_groups_list_keeps_every_topic_as_is():
    topics = [_topic("A", [1], "chunk_1"), _topic("B", [2], "chunk_2")]
    mock_reply = json.dumps({"groups": []})

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        result = await normalize_and_deduplicate(topics)

    assert result == topics


@pytest.mark.asyncio
async def test_rejects_response_that_double_assigns_an_index():
    topics = [_topic("A", [1], "chunk_1"), _topic("B", [2], "chunk_2")]
    mock_reply = json.dumps(
        {
            "groups": [
                {"name": "A", "indices": [0, 1]},
                {"name": "B", "indices": [1]},
            ]
        }
    )

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        with pytest.raises(TopicNormalizationError):
            await normalize_and_deduplicate(topics)


@pytest.mark.asyncio
async def test_wraps_gateway_failure():
    topics = [_topic("A", [1], "chunk_1"), _topic("B", [2], "chunk_2")]

    with patch.object(gateway, "generate", new=AsyncMock(side_effect=RuntimeError("all providers down"))):
        with pytest.raises(TopicNormalizationError):
            await normalize_and_deduplicate(topics)
