"""
Unit and integration tests for the AI Topic Organizer Service and API route.
Completely mocked (zero real LLM calls / tokens consumed).
"""

import json
import pytest
from unittest.mock import patch, AsyncMock

from httpx import ASGITransport, AsyncClient

from src.app.main import app
from src.app.services.topic_organizer_service import (
    TopicOrganizerService,
    TopicOrganizerError,
)
from src.app.schemas.topics import OrganizeTopicItem, OrganizeSectionItem


@pytest.fixture
def anyio_backend():
    return "asyncio"


TOPICS = [
    OrganizeTopicItem(id="t1", name="React"),
    OrganizeTopicItem(id="t2", name="JavaScript"),
    OrganizeTopicItem(id="t3", name="TypeScript"),
]


@pytest.mark.asyncio
async def test_organize_returns_reordered_ids():
    service = TopicOrganizerService()
    mock_reply = json.dumps({"order": [1, 2, 0], "reasoning": "Learn fundamentals first."})

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        result = await service.organize("Frontend Interview", "Interview", TOPICS)

    assert result.ordered_topic_ids == ["t2", "t3", "t1"]
    assert result.reasoning == "Learn fundamentals first."
    assert result.provider == "Groq"
    assert result.model == "test-model"


@pytest.mark.asyncio
async def test_organize_tolerates_prose_and_fences_around_json():
    service = TopicOrganizerService()
    mock_reply = 'Sure, here is the order:\n```json\n{"order": [2, 0, 1]}\n```\nHope that helps!'

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        result = await service.organize("Frontend Interview", "Interview", TOPICS)

    assert result.ordered_topic_ids == ["t3", "t1", "t2"]


@pytest.mark.asyncio
async def test_organize_rejects_invalid_permutation():
    service = TopicOrganizerService()
    mock_reply = json.dumps({"order": [0, 0, 1]})

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        with pytest.raises(TopicOrganizerError):
            await service.organize("Frontend Interview", "Interview", TOPICS)


@pytest.mark.asyncio
async def test_organize_rejects_wrong_length_order():
    service = TopicOrganizerService()
    mock_reply = json.dumps({"order": [0, 1]})

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        with pytest.raises(TopicOrganizerError):
            await service.organize("Frontend Interview", "Interview", TOPICS)


@pytest.mark.asyncio
async def test_organize_rejects_non_json_reply():
    service = TopicOrganizerService()

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=("I cannot help with that.", "Groq", "test-model", {}, [])),
    ):
        with pytest.raises(TopicOrganizerError):
            await service.organize("Frontend Interview", "Interview", TOPICS)


@pytest.mark.asyncio
async def test_organize_requires_at_least_two_topics():
    service = TopicOrganizerService()
    with pytest.raises(TopicOrganizerError):
        await service.organize("Frontend Interview", "Interview", TOPICS[:1])


@pytest.mark.asyncio
async def test_organize_returns_section_assignments():
    service = TopicOrganizerService()
    mock_reply = json.dumps(
        {
            "order": [1, 2, 0],
            "sections": ["Frontend", "JS Fundamentals"],
            "topic_section_indices": [0, 0, 1],
            "reasoning": "Grouped by layer.",
        }
    )

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        result = await service.organize(
            "Frontend Interview",
            "Interview",
            TOPICS,
            sections=[OrganizeSectionItem(id="s1", name="JS Fundamentals")],
        )

    # section_assignments is indexed in INPUT topic order (t1, t2, t3), not output order.
    assignments = {a.topic_id: a.section_name for a in result.section_assignments}
    assert assignments == {
        "t1": "Frontend",
        "t2": "Frontend",
        "t3": "JS Fundamentals",
    }


@pytest.mark.asyncio
async def test_organize_falls_back_to_ungrouped_on_malformed_sections():
    service = TopicOrganizerService()
    # topic_section_indices is the wrong length -- should not fail the whole
    # (already-valid) ordering.
    mock_reply = json.dumps(
        {"order": [1, 2, 0], "sections": ["Frontend"], "topic_section_indices": [0]}
    )

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        result = await service.organize("Frontend Interview", "Interview", TOPICS)

    assert result.ordered_topic_ids == ["t2", "t3", "t1"]
    assert all(a.section_name is None for a in result.section_assignments)


@pytest.mark.asyncio
async def test_organize_falls_back_to_ungrouped_on_out_of_range_section_index():
    service = TopicOrganizerService()
    mock_reply = json.dumps(
        {
            "order": [1, 2, 0],
            "sections": ["Frontend"],
            "topic_section_indices": [0, 5, 0],  # 5 is out of range
        }
    )

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        result = await service.organize("Frontend Interview", "Interview", TOPICS)

    assert result.ordered_topic_ids == ["t2", "t3", "t1"]
    assert all(a.section_name is None for a in result.section_assignments)


@pytest.mark.asyncio
async def test_organize_wraps_gateway_failure():
    service = TopicOrganizerService()

    with patch.object(
        service.gateway,
        "generate",
        new=AsyncMock(side_effect=RuntimeError("All LLM providers are currently unavailable")),
    ):
        with pytest.raises(TopicOrganizerError) as exc_info:
            await service.organize("Frontend Interview", "Interview", TOPICS)

    assert exc_info.value.status_code == 502


# -----------------------------------------------------------------------------
# API-level tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_organize_endpoint_success():
    mock_reply = json.dumps({"order": [1, 2, 0], "reasoning": "Fundamentals first."})

    with patch(
        "src.app.services.topic_organizer_service.topic_organizer_service.gateway.generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "preparation_title": "Frontend Interview",
                "preparation_type": "Interview",
                "topics": [
                    {"id": "t1", "name": "React"},
                    {"id": "t2", "name": "JavaScript"},
                    {"id": "t3", "name": "TypeScript"},
                ],
            }
            response = await client.post("/api/topics/organize", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["ordered_topic_ids"] == ["t2", "t3", "t1"]
            assert data["reasoning"] == "Fundamentals first."


@pytest.mark.asyncio
async def test_organize_endpoint_returns_section_assignments():
    mock_reply = json.dumps(
        {
            "order": [1, 2, 0],
            "sections": ["Frontend", "JS Fundamentals"],
            "topic_section_indices": [0, 0, 1],
            "reasoning": "Grouped by layer.",
        }
    )

    with patch(
        "src.app.services.topic_organizer_service.topic_organizer_service.gateway.generate",
        new=AsyncMock(return_value=(mock_reply, "Groq", "test-model", {}, [])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "preparation_title": "Frontend Interview",
                "topics": [
                    {"id": "t1", "name": "React"},
                    {"id": "t2", "name": "JavaScript"},
                    {"id": "t3", "name": "TypeScript"},
                ],
                "sections": [{"id": "s1", "name": "JS Fundamentals"}],
            }
            response = await client.post("/api/topics/organize", json=payload)
            assert response.status_code == 200
            data = response.json()
            assignments = {
                a["topic_id"]: a["section_name"] for a in data["section_assignments"]
            }
            assert assignments == {
                "t1": "Frontend",
                "t2": "Frontend",
                "t3": "JS Fundamentals",
            }


@pytest.mark.asyncio
async def test_organize_endpoint_rejects_single_topic():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"preparation_title": "X", "topics": [{"id": "t1", "name": "React"}]}
        response = await client.post("/api/topics/organize", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_organize_endpoint_maps_invalid_ai_response_to_502():
    with patch(
        "src.app.services.topic_organizer_service.topic_organizer_service.gateway.generate",
        new=AsyncMock(return_value=("not json at all", "Groq", "test-model", {}, [])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "preparation_title": "Frontend Interview",
                "topics": [{"id": "t1", "name": "React"}, {"id": "t2", "name": "JavaScript"}],
            }
            response = await client.post("/api/topics/organize", json=payload)
            assert response.status_code == 502
