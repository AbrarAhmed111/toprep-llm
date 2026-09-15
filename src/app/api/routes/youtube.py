"""
YouTube Search API Endpoints.
Thin route handlers delegating to youtube_service.
"""

from fastapi import APIRouter, HTTPException, status
from src.app.schemas.youtube import YouTubeSearchRequest, YouTubeSearchResponse
from src.app.services.youtube_service import youtube_service, YouTubeAPIError

router = APIRouter(prefix="/youtube", tags=["YouTube"])


@router.post("/search", response_model=YouTubeSearchResponse, summary="Search YouTube Videos for a Topic")
async def search_youtube(request: YouTubeSearchRequest) -> YouTubeSearchResponse:
    """
    Searches YouTube for videos relevant to a topic, applying duration, view count,
    published date, language, shorts/livestream, and sort filters.
    """
    try:
        return await youtube_service.search(topic=request.topic, filters=request.filters)
    except YouTubeAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YouTube Search Failed: {str(e)}",
        )
