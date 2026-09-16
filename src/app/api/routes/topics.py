"""
Topic Organization & PDF Topic Extraction API Endpoints.
Thin route handlers delegating to topic_organizer_service / pdf_extraction_service.
"""

import asyncio

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from src.app.core.config import get_settings
from src.app.schemas.pdf import PdfTopicsResponse
from src.app.schemas.topics import TopicOrganizeRequest, TopicOrganizeResponse
from src.app.services.pdf.extractor import PdfExtractionError
from src.app.services.pdf_extraction_service import extract_topics_from_pdf
from src.app.services.topic_extraction.extractor import TopicExtractionError
from src.app.services.topic_extraction.normalizer import TopicNormalizationError
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


@router.post(
    "/extract-pdf",
    response_model=PdfTopicsResponse,
    summary="Extract Learning Topics from an Uploaded PDF",
)
async def extract_pdf_topics(file: UploadFile = File(...)) -> PdfTopicsResponse:
    """
    Accepts an uploaded PDF and returns a flat, deduplicated list of extracted
    learning topic names, ready to feed into the bulk-add-topics flow.
    """
    filename = (file.filename or "").lower()
    looks_like_pdf = file.content_type == "application/pdf" or filename.endswith(".pdf")
    if not looks_like_pdf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a PDF file.",
        )

    file_bytes = await file.read()

    try:
        topics = await asyncio.wait_for(
            extract_topics_from_pdf(file_bytes),
            timeout=get_settings().PDF_PIPELINE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Extracting topics from this PDF took too long. Try a shorter document.",
        )
    except (PdfExtractionError, TopicExtractionError, TopicNormalizationError) as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF topic extraction failed: {str(e)}",
        )

    return PdfTopicsResponse(topics=topics)
