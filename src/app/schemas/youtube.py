"""
Pydantic Schemas for YouTube Topic Search & Filtering.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class PublishedWindow(str, Enum):
    """Relative publish-date window, mirroring common YouTube search filters."""
    ANY_TIME = "any_time"
    PAST_MONTH = "past_month"
    PAST_6_MONTHS = "past_6_months"
    PAST_YEAR = "past_year"
    CUSTOM = "custom"


class SortOrder(str, Enum):
    """Result ordering strategy."""
    RELEVANCE = "relevance"
    VIEWS = "views"
    NEWEST = "newest"
    OLDEST = "oldest"


class YouTubeSearchFilters(BaseModel):
    """Filter and sort options for a topic video search."""
    min_duration_seconds: Optional[int] = Field(None, ge=0, description="Minimum video duration in seconds")
    max_duration_seconds: Optional[int] = Field(None, ge=0, description="Maximum video duration in seconds")
    min_views: Optional[int] = Field(None, ge=0, description="Minimum view count")
    max_views: Optional[int] = Field(None, ge=0, description="Maximum view count")
    published_window: PublishedWindow = Field(
        PublishedWindow.ANY_TIME, description="Relative publish-date window"
    )
    published_after: Optional[datetime] = Field(
        None, description="Custom range start (used when published_window is 'custom')"
    )
    published_before: Optional[datetime] = Field(
        None, description="Custom range end (used when published_window is 'custom')"
    )
    language: Optional[str] = Field(
        None, description="ISO 639-1 language hint for search relevance, e.g. 'en'"
    )
    exclude_shorts: bool = Field(False, description="Exclude videos 60 seconds or shorter")
    exclude_livestreams: bool = Field(True, description="Exclude currently-live and upcoming streams")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of videos to return")
    sort: SortOrder = Field(SortOrder.RELEVANCE, description="Result ordering strategy")


class YouTubeVideo(BaseModel):
    """A single YouTube video result enriched with duration, views, and live status."""
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    thumbnail_url: str
    published_at: datetime
    duration_seconds: int
    view_count: int
    is_short: bool
    is_live: bool
    url: str


class YouTubeSearchRequest(BaseModel):
    """Request payload for a topic-scoped YouTube search."""
    topic: str = Field(..., min_length=1, description="Topic name or search query")
    filters: YouTubeSearchFilters = Field(default_factory=YouTubeSearchFilters)


class YouTubeSearchResponse(BaseModel):
    """Filtered and sorted YouTube search results for a topic."""
    topic: str
    total_results: int
    videos: List[YouTubeVideo]
