"""
YouTube Search Service.
Fetches videos relevant to a topic from the YouTube Data API v3, enriches
raw search hits with duration / view-count / live-status via the videos
endpoint, then applies the requested filters and sort order.
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx

from src.app.core.config import get_settings
from src.app.schemas.youtube import (
    PublishedWindow,
    SortOrder,
    YouTubeSearchFilters,
    YouTubeSearchResponse,
    YouTubeVideo,
)

logger = logging.getLogger("YouTubeService")

# Matches ISO 8601 durations as returned by the YouTube API, e.g. "PT4M13S", "PT1H2M10S".
ISO8601_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)

# YouTube treats videos at or under this length as "Shorts".
SHORT_DURATION_THRESHOLD_SECONDS = 60

_SORT_TO_API_ORDER = {
    SortOrder.RELEVANCE: "relevance",
    SortOrder.VIEWS: "viewCount",
    SortOrder.NEWEST: "date",
    SortOrder.OLDEST: "date",  # YouTube has no native oldest-first order; sorted locally below.
}


class YouTubeAPIError(Exception):
    """Raised when the YouTube Data API cannot fulfill a search request."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def parse_iso8601_duration(value: Optional[str]) -> int:
    """Converts an ISO 8601 duration string (e.g. 'PT4M13S') into whole seconds."""
    if not value:
        return 0
    match = ISO8601_DURATION_RE.match(value)
    if not match:
        return 0
    parts = match.groupdict()
    days, hours, minutes, seconds = (int(parts[k] or 0) for k in ("days", "hours", "minutes", "seconds"))
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _resolve_published_after(filters: YouTubeSearchFilters) -> Optional[datetime]:
    """Resolves the effective 'publishedAfter' cutoff for the configured window."""
    if filters.published_window == PublishedWindow.CUSTOM:
        return filters.published_after

    now = datetime.now(timezone.utc)
    if filters.published_window == PublishedWindow.PAST_MONTH:
        return now - timedelta(days=30)
    if filters.published_window == PublishedWindow.PAST_6_MONTHS:
        return now - timedelta(days=182)
    if filters.published_window == PublishedWindow.PAST_YEAR:
        return now - timedelta(days=365)
    return None  # ANY_TIME


class YouTubeService:
    """Searches YouTube for videos relevant to a topic and applies filters/sorting."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.YOUTUBE_API_KEY
        self.base_url = settings.YOUTUBE_API_BASE_URL
        self.timeout = settings.YOUTUBE_REQUEST_TIMEOUT
        self.default_max_results = settings.YOUTUBE_DEFAULT_MAX_RESULTS
        self.max_results_limit = settings.YOUTUBE_MAX_RESULTS_LIMIT

    async def search(self, topic: str, filters: YouTubeSearchFilters) -> YouTubeSearchResponse:
        """Searches YouTube for `topic`, enriches, filters, sorts, and caps results."""
        if not self.api_key or not self.api_key.strip():
            raise YouTubeAPIError("YouTube API key is not configured.", status_code=503)

        requested = min(filters.max_results or self.default_max_results, self.max_results_limit)
        # Over-fetch so that post-filtering (duration/views/shorts/live) still
        # leaves enough candidates to satisfy the requested count.
        fetch_count = min(max(requested * 3, requested), 50)

        candidate_ids = await self._search_video_ids(topic=topic, filters=filters, fetch_count=fetch_count)
        if not candidate_ids:
            return YouTubeSearchResponse(topic=topic, total_results=0, videos=[])

        videos = await self._fetch_video_details(candidate_ids)
        filtered = self._apply_filters(videos, filters)
        sorted_videos = self._sort_videos(filtered, filters.sort)
        final = sorted_videos[:requested]

        logger.info(
            f"🔎 YouTube search for \"{topic}\": {len(candidate_ids)} candidates -> "
            f"{len(filtered)} after filters -> {len(final)} returned."
        )

        return YouTubeSearchResponse(topic=topic, total_results=len(final), videos=final)

    async def _search_video_ids(self, topic: str, filters: YouTubeSearchFilters, fetch_count: int) -> List[str]:
        """Calls search.list to find candidate video IDs for the topic."""
        params = {
            "key": self.api_key,
            "part": "snippet",
            "q": topic,
            "type": "video",
            "maxResults": fetch_count,
            "order": _SORT_TO_API_ORDER[filters.sort],
        }

        published_after = _resolve_published_after(filters)
        if published_after:
            params["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")
        if filters.published_window == PublishedWindow.CUSTOM and filters.published_before:
            params["publishedBefore"] = filters.published_before.strftime("%Y-%m-%dT%H:%M:%SZ")
        if filters.language:
            params["relevanceLanguage"] = filters.language
        if filters.exclude_livestreams:
            # "completed" restricts results to regular (non-live, non-upcoming) videos.
            params["eventType"] = "completed"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/search", params=params)

        self._raise_for_error(response)
        data = response.json()
        return [
            item["id"]["videoId"]
            for item in data.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

    async def _fetch_video_details(self, video_ids: List[str]) -> List[YouTubeVideo]:
        """Calls videos.list to enrich candidate IDs with duration, views, and live status."""
        params = {
            "key": self.api_key,
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/videos", params=params)

        self._raise_for_error(response)
        data = response.json()

        videos: List[YouTubeVideo] = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            statistics = item.get("statistics", {})
            video_id = item.get("id", "")

            duration_seconds = parse_iso8601_duration(content_details.get("duration"))
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
                or ""
            )

            videos.append(
                YouTubeVideo(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    channel_id=snippet.get("channelId", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    thumbnail_url=thumbnail_url,
                    published_at=snippet.get("publishedAt"),
                    duration_seconds=duration_seconds,
                    view_count=int(statistics.get("viewCount", 0) or 0),
                    is_short=0 < duration_seconds <= SHORT_DURATION_THRESHOLD_SECONDS,
                    is_live=snippet.get("liveBroadcastContent", "none") != "none",
                    url=f"https://www.youtube.com/watch?v={video_id}",
                )
            )
        return videos

    def _apply_filters(self, videos: List[YouTubeVideo], filters: YouTubeSearchFilters) -> List[YouTubeVideo]:
        """Applies duration, view-count, shorts, and livestream filters."""
        result = videos
        if filters.min_duration_seconds is not None:
            result = [v for v in result if v.duration_seconds >= filters.min_duration_seconds]
        if filters.max_duration_seconds is not None:
            result = [v for v in result if v.duration_seconds <= filters.max_duration_seconds]
        if filters.min_views is not None:
            result = [v for v in result if v.view_count >= filters.min_views]
        if filters.max_views is not None:
            result = [v for v in result if v.view_count <= filters.max_views]
        if filters.exclude_shorts:
            result = [v for v in result if not v.is_short]
        if filters.exclude_livestreams:
            result = [v for v in result if not v.is_live]
        return result

    def _sort_videos(self, videos: List[YouTubeVideo], sort: SortOrder) -> List[YouTubeVideo]:
        """Applies the final local sort (YouTube has no native oldest-first order)."""
        if sort == SortOrder.VIEWS:
            return sorted(videos, key=lambda v: v.view_count, reverse=True)
        if sort == SortOrder.NEWEST:
            return sorted(videos, key=lambda v: v.published_at, reverse=True)
        if sort == SortOrder.OLDEST:
            return sorted(videos, key=lambda v: v.published_at)
        return videos  # RELEVANCE: preserve YouTube's own ranking order

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        """Raises a YouTubeAPIError with a mapped status code for non-200 responses."""
        if response.status_code == 200:
            return
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        status_code = 429 if response.status_code == 403 and "quota" in detail.lower() else 502
        logger.error(f"❌ YouTube API error ({response.status_code}): {detail}")
        raise YouTubeAPIError(f"YouTube API error: {detail}", status_code=status_code)


# Singleton instance
youtube_service = YouTubeService()
