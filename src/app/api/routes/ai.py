"""
AI Features API Endpoints.
Thin route handlers delegating to ai_service.
"""

from fastapi import APIRouter, HTTPException, status
from src.app.schemas.ai import (
    AIExplanationRequest,
    AIExplanationResponse,
    AIQuestionsRequest,
    AIQuestionsResponse,
)
from src.app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI Features"])


@router.post("/explain", response_model=AIExplanationResponse, summary="Generate Topic Explanation")
async def generate_explanation(request: AIExplanationRequest) -> AIExplanationResponse:
    """
    Generate a brief (2-3 line) AI explanation for a topic.

    The explanation is beginner-friendly and contextual to the preparation type.
    Uses multi-provider LLM Gateway with automatic failover.
    """
    try:
        return await ai_service.generate_explanation(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanation: {str(e)}",
        )


@router.post("/questions", response_model=AIQuestionsResponse, summary="Generate Expected Questions")
async def generate_questions(request: AIQuestionsRequest) -> AIQuestionsResponse:
    """
    Generate 3-5 expected interview/exam questions for a topic.

    Questions are realistic and tailored to the preparation type and context.
    Uses multi-provider LLM Gateway with automatic failover.
    """
    try:
        return await ai_service.generate_questions(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {str(e)}",
        )
