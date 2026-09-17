"""
Topic Organization & PDF Topic Extraction API Endpoints.
Thin route handlers delegating to topic_organizer_service / pdf_extraction_service.
"""

import asyncio
import json
import time

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from src.app.core.config import get_settings
from src.app.schemas.topics import TopicOrganizeRequest, TopicOrganizeResponse
from src.app.services.pdf_extraction_service import stream_topics_from_pdf
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


_TIMEOUT_EVENT_TEMPLATE = {
    "stage": "error",
    "status": "error",
    "message": "Extracting topics from this PDF took too long. Try a shorter document.",
    "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
}


@router.post(
    "/extract-pdf",
    summary="Extract Learning Topics from an Uploaded PDF (Server-Sent Events)",
)
async def extract_pdf_topics(file: UploadFile = File(...)) -> StreamingResponse:
    """
    Accepts an uploaded PDF and streams pipeline progress as newline-delimited
    Server-Sent Events (`data: {...}\\n\\n`) -- one per stage of
    stream_topics_from_pdf -- ending in either a `{"stage": "complete", ...,
    "topics": [...]}` event or a `{"stage": "error", ...}` one. See
    stream_topics_from_pdf's docstring for the full event shape.

    A malformed upload (not a PDF by content-type/filename) is rejected
    up front with a normal 400, before any streaming begins -- everything
    that can only be discovered once the pipeline is running (corrupt PDF,
    AI failures, timeouts) surfaces as an in-stream error event instead,
    since the 200 + event-stream headers are already committed by then.
    """
    filename = (file.filename or "").lower()
    looks_like_pdf = file.content_type == "application/pdf" or filename.endswith(".pdf")
    if not looks_like_pdf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a PDF file.",
        )

    file_bytes = await file.read()
    deadline = time.monotonic() + get_settings().PDF_PIPELINE_TIMEOUT_SECONDS

    async def event_source():
        pipeline = stream_topics_from_pdf(file_bytes)
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    yield f"data: {json.dumps(_TIMEOUT_EVENT_TEMPLATE)}\n\n"
                    return
                try:
                    event = await asyncio.wait_for(pipeline.__anext__(), timeout=remaining)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps(_TIMEOUT_EVENT_TEMPLATE)}\n\n"
                    return
                except StopAsyncIteration:
                    return
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("stage") in ("complete", "error"):
                    return
        finally:
            await pipeline.aclose()

    return StreamingResponse(event_source(), media_type="text/event-stream")
