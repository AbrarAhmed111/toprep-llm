"""
AI Features API Endpoints.
Thin route handlers delegating to ai_service.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from src.app.schemas.ai import (
    AIExplanationRequest,
    AIExplanationResponse,
    AIQuestionsRequest,
    AIQuestionsResponse,
)
from src.app.services.ai_service import ai_service

logger = logging.getLogger("AIRouter")
router = APIRouter(prefix="/ai", tags=["AI Features"])


@router.post("/explain", response_model=AIExplanationResponse, summary="Generate Topic Explanation")
async def generate_explanation(request: AIExplanationRequest) -> AIExplanationResponse:
    """
    Generate a brief (2-3 line) AI explanation for a topic.

    The explanation is beginner-friendly and contextual to the preparation type.
    Uses multi-provider LLM Gateway with automatic failover.
    """
    logger.debug(f"📨 Received explanation request for: {request.topic_name}")
    try:
        result = await ai_service.generate_explanation(request)
        logger.debug(f"📤 Returning explanation response for: {request.topic_name}")
        return result
    except Exception as e:
        logger.error(f"🚨 Explanation endpoint error: {type(e).__name__}: {str(e)}")
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
    logger.debug(f"📨 Received questions request for: {request.topic_name}")
    try:
        result = await ai_service.generate_questions(request)
        logger.debug(f"📤 Returning questions response for: {request.topic_name}")
        return result
    except Exception as e:
        logger.error(f"🚨 Questions endpoint error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {str(e)}",
        )
