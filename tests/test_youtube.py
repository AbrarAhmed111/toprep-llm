"""
Unit and integration tests for the YouTube Search Service and API route.
Completely mocked (zero real YouTube API calls / quota consumed).
"""

import pytest
from unittest.mock import patch, MagicMock

from httpx import ASGITransport, AsyncClient

from src.app.main import app
from src.app.services.youtube_service import (
    YouTubeService,
    YouTubeAPIError,
    parse_iso8601_duration,
)
from src.app.schemas.youtube import YouTubeSearchFilters, SortOrder


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -----------------------------------------------------------------------------
# Duration Parsing
# -----------------------------------------------------------------------------
def test_parse_duration_minutes_seconds():
    assert parse_iso8601_duration("PT4M13S") == 253


def test_parse_duration_hours_minutes_seconds():
    assert parse_iso8601_duration("PT1H2M10S") == 3730


def test_parse_duration_seconds_only():
    assert parse_iso8601_duration("PT45S") == 45


def test_parse_duration_invalid_or_missing_returns_zero():
    assert parse_iso8601_duration("") == 0
    assert parse_iso8601_duration(None) == 0
    assert parse_iso8601_duration("not-a-duration") == 0


# -----------------------------------------------------------------------------
# Fixtures: canned YouTube Data API responses
# -----------------------------------------------------------------------------
SEARCH_PAYLOAD = {
    "items": [
        {"id": {"videoId": "vid_long"}},
        {"id": {"videoId": "vid_short"}},
    ]
}

VIDEOS_PAYLOAD = {
    "items": [
        {
            "id": "vid_long",
            "snippet": {
                "title": "Deep Dive Tutorial",
                "description": "A thorough walkthrough.",
                "channelId": "chan1",
                "channelTitle": "Channel One",
                "thumbnails": {"high": {"url": "http://img/high1.jpg"}},
                "publishedAt": "2024-01-01T00:00:00Z",
                "liveBroadcastContent": "none",
            },
            "contentDetails": {"duration": "PT15M30S"},
            "statistics": {"viewCount": "1000"},
        },
        {
            "id": "vid_short",
            "snippet": {
                "title": "Quick Tip",
                "description": "A 45 second short.",
                "channelId": "chan2",
                "channelTitle": "Channel Two",
                "thumbnails": {"high": {"url": "http://img/high2.jpg"}},
                "publishedAt": "2024-06-01T00:00:00Z",
                "liveBroadcastContent": "none",
            },
            "contentDetails": {"duration": "PT45S"},
            "statistics": {"viewCount": "5000"},
        },
    ]
}


def _mock_response(status_code: int, payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = str(payload)
    return resp


@pytest.fixture
def mock_youtube_http():
    """Patches httpx.AsyncClient.get to return canned search/videos responses."""

    async def fake_get(self, url, params=None, **kwargs):
        if url.endswith("/search"):
            return _mock_response(200, SEARCH_PAYLOAD)
        if url.endswith("/videos"):
            return _mock_response(200, VIDEOS_PAYLOAD)
        raise AssertionError(f"Unexpected URL requested: {url}")

    with patch("httpx.AsyncClient.get", new=fake_get):
        yield


# -----------------------------------------------------------------------------
# Service-level tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_service_filters_out_shorts(mock_youtube_http):
    service = YouTubeService()
    service.api_key = "test-key"

    filters = YouTubeSearchFilters(exclude_shorts=True, sort=SortOrder.VIEWS, max_results=10)
    result = await service.search(topic="React hooks", filters=filters)

    assert result.topic == "React hooks"
    assert len(result.videos) == 1
    assert result.videos[0].video_id == "vid_long"
    assert result.videos[0].is_short is False


@pytest.mark.asyncio
async def test_service_sorts_by_views_descending(mock_youtube_http):
    service = YouTubeService()
    service.api_key = "test-key"

    filters = YouTubeSearchFilters(sort=SortOrder.VIEWS, max_results=10)
    result = await service.search(topic="React hooks", filters=filters)

    assert [v.video_id for v in result.videos] == ["vid_short", "vid_long"]


@pytest.mark.asyncio
async def test_service_respects_max_results(mock_youtube_http):
    service = YouTubeService()
    service.api_key = "test-key"

    filters = YouTubeSearchFilters(max_results=1)
    result = await service.search(topic="React hooks", filters=filters)

    assert len(result.videos) == 1


@pytest.mark.asyncio
async def test_service_raises_when_api_key_missing():
    service = YouTubeService()
    service.api_key = ""

    with pytest.raises(YouTubeAPIError):
        await service.search(topic="React hooks", filters=YouTubeSearchFilters())


@pytest.mark.asyncio
async def test_service_maps_quota_error_to_429():
    async def fake_get_quota_exceeded(self, url, params=None, **kwargs):
        return _mock_response(403, {"error": {"message": "Quota exceeded for this project"}})

    service = YouTubeService()
    service.api_key = "test-key"

    with patch("httpx.AsyncClient.get", new=fake_get_quota_exceeded):
        with pytest.raises(YouTubeAPIError) as exc_info:
            await service.search(topic="React hooks", filters=YouTubeSearchFilters())

    assert exc_info.value.status_code == 429


# -----------------------------------------------------------------------------
# API-level tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_endpoint_returns_filtered_videos(mock_youtube_http):
    with patch("src.app.services.youtube_service.youtube_service.api_key", "test-key"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "topic": "React hooks",
                "filters": {"exclude_shorts": True, "max_results": 10},
            }
            response = await client.post("/api/youtube/search", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["topic"] == "React hooks"
            assert len(data["videos"]) == 1
            assert data["videos"][0]["video_id"] == "vid_long"


@pytest.mark.asyncio
async def test_search_endpoint_rejects_empty_topic():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/youtube/search", json={"topic": ""})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_returns_503_without_api_key():
    with patch("src.app.services.youtube_service.youtube_service.api_key", ""):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/youtube/search", json={"topic": "React hooks"})
            assert response.status_code == 503
