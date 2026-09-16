"""
Unit tests for LLM-based topic extraction from PDF chunks.
Completely mocked (zero real LLM calls / tokens consumed). Mocks are
applied to the shared `chat_service.gateway` singleton -- the same
multi-provider, automatic-failover gateway used by chat and topic
organization -- to confirm extraction goes through it rather than a
separate LLM client.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.app.schemas.pdf import PdfChunk
from src.app.services.chat_service import gateway
from src.app.services.topic_extraction.extractor import (
    TopicExtractionError,
    extract_topics,
    extract_topics_from_chunk,
)


def _chunk(chunk_id="chunk_1", pages=(1, 2), heading=None, text="Some section content."):
    return PdfChunk(chunk_id=chunk_id, heading=heading, pages=list(pages), text=text)


@pytest.mark.asyncio
async def test_extract_topics_from_chunk_returns_topics_with_provenance():
    mock_reply = json.dumps({"topics": ["React Hooks", "useState"]})

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        topics = await extract_topics_from_chunk(_chunk(chunk_id="chunk_3", pages=(5, 6)))

    assert [t.name for t in topics] == ["React Hooks", "useState"]
    assert all(t.source_pages == [5, 6] for t in topics)
    assert all(t.chunk_ids == ["chunk_3"] for t in topics)


@pytest.mark.asyncio
async def test_extract_topics_from_chunk_tolerates_prose_and_fences():
    mock_reply = 'Sure! Here you go:\n```json\n{"topics": ["Closures"]}\n```\nHope that helps.'

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        topics = await extract_topics_from_chunk(_chunk())

    assert [t.name for t in topics] == ["Closures"]


@pytest.mark.asyncio
async def test_extract_topics_from_chunk_skips_empty_chunk_without_calling_llm():
    with patch.object(gateway, "generate", new=AsyncMock()) as mock_generate:
        topics = await extract_topics_from_chunk(_chunk(text="   "))

    mock_generate.assert_not_called()
    assert topics == []


@pytest.mark.asyncio
async def test_extract_topics_from_chunk_rejects_missing_topics_array():
    mock_reply = json.dumps({"unexpected": []})

    with patch.object(
        gateway, "generate", new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, []))
    ):
        with pytest.raises(TopicExtractionError):
            await extract_topics_from_chunk(_chunk())


@pytest.mark.asyncio
async def test_extract_topics_from_chunk_wraps_gateway_failure():
    with patch.object(gateway, "generate", new=AsyncMock(side_effect=RuntimeError("all providers down"))):
        with pytest.raises(TopicExtractionError):
            await extract_topics_from_chunk(_chunk())


@pytest.mark.asyncio
async def test_extract_topics_aggregates_across_chunks():
    replies = [
        (json.dumps({"topics": ["React Hooks"]}), "Groq", "test-model", {}, []),
        (json.dumps({"topics": ["JavaScript Promises"]}), "Groq", "test-model", {}, []),
    ]

    with patch.object(gateway, "generate", new=AsyncMock(side_effect=replies)):
        topics = await extract_topics(
            [
                _chunk(chunk_id="chunk_1", pages=(1, 2)),
                _chunk(chunk_id="chunk_2", pages=(3, 4)),
            ]
        )

    assert [t.name for t in topics] == ["React Hooks", "JavaScript Promises"]
    assert topics[0].chunk_ids == ["chunk_1"]
    assert topics[1].chunk_ids == ["chunk_2"]
