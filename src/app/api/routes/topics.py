"""
Topic Organization API Endpoints.
Thin route handlers delegating to topic_organizer_service.
"""

from fastapi import APIRouter, HTTPException, status
from src.app.schemas.topics import TopicOrganizeRequest, TopicOrganizeResponse
from src.app.services.topic_organizer_service import (
    topic_organizer_service,
    TopicOrganizerError,
)

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.post("/organize", response_model=TopicOrganizeResponse, summary="Suggest an AI Topic Order")
async def organize_topics(request: TopicOrganizeRequest) -> TopicOrganizeResponse:
    """
    Proposes a learning order for the given topics based on prerequisites,
    dependencies, and conceptual progression. Ordering only — the caller
    must explicitly accept the suggestion before applying it.
    """
    try:
        return await topic_organizer_service.organize(
            preparation_title=request.preparation_title,
            preparation_type=request.preparation_type,
            topics=request.topics,
            sections=request.sections,
        )
    except TopicOrganizerError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Topic Organization Failed: {str(e)}",
        )
