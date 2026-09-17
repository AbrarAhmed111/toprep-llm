"""
API-level tests for POST /api/topics/extract-pdf.
Completely mocked LLM calls (patched on the shared chat_service.gateway
singleton) -- verifies the endpoint contract the frontend relies on
(pdfExtraction.ts): multipart `file` in, a Server-Sent Events stream of
progress events out, ending in either a "complete" event with `topics` or
an "error" event with a user-readable `message` and `status_code`.
"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pymupdf
import pytest
from httpx import ASGITransport, AsyncClient

from src.app.core.config import get_settings
from src.app.main import app
from src.app.services.chat_service import gateway


def _build_pdf_bytes(page_texts):
    doc = pymupdf.open()
    for text in page_texts:
        doc.new_page().insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _parse_sse_events(raw_text: str) -> List[Dict[str, Any]]:
    events = []
    for line in raw_text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_streams_progress_then_deduplicated_topics():
    pdf_bytes = _build_pdf_bytes(
        [
            "React Hooks let you use state in function components.",
            "Promises represent the eventual completion of an async operation.",
        ]
    )
    extraction_reply = json.dumps({"topics": ["React Hooks", "JavaScript Promises"]})
    normalization_reply = json.dumps({"groups": []})
    grouping_reply = json.dumps(
        {
            "order": [0, 1],
            "sections": ["Frontend Basics"],
            "topic_section_indices": [0, 0],
        }
    )

    with patch.object(
        gateway,
        "generate",
        new=AsyncMock(
            side_effect=[
                (extraction_reply, "Groq", "test-model", {}, []),
                (normalization_reply, "Groq", "test-model", {}, []),
                (grouping_reply, "Groq", "test-model", {}, []),
            ]
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/topics/extract-pdf",
                files={"file": ("guide.pdf", pdf_bytes, "application/pdf")},
            )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_events(response.text)
    stages = [e["stage"] for e in events]
    assert stages == [
        "validating",
        "validating",
        "reading",
        "reading",
        "analyzing",
        "analyzing",
        "organizing",
        "organizing",
        "grouping",
        "grouping",
        "complete",
    ]
    assert events[-1] == {
        "stage": "complete",
        "status": "done",
        "topics": [
            {"name": "React Hooks", "section": "Frontend Basics"},
            {"name": "JavaScript Promises", "section": "Frontend Basics"},
        ],
    }


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_rejects_non_pdf_upload():
    with patch.object(gateway, "generate", new=AsyncMock()) as mock_generate:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/topics/extract-pdf",
                files={"file": ("notes.txt", b"just some plain text", "text/plain")},
            )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]
    mock_generate.assert_not_called()


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_streams_readable_error_for_corrupt_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/topics/extract-pdf",
            files={"file": ("guide.pdf", b"this is not really a pdf", "application/pdf")},
        )

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    error_event = events[-1]
    assert error_event["stage"] == "error"
    assert error_event["status_code"] == 422
    assert "could not be processed" in error_event["message"].lower()
    assert "Traceback" not in error_event["message"]


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_streams_timeout_error_on_slow_pipeline(monkeypatch):
    monkeypatch.setattr(get_settings(), "PDF_PIPELINE_TIMEOUT_SECONDS", 0.05)

    async def _slow_pipeline(_file_bytes):
        await asyncio.sleep(0.3)
        yield {"stage": "complete", "status": "done", "topics": ["Should never be reached"]}

    with patch("src.app.api.routes.topics.stream_topics_from_pdf", new=_slow_pipeline):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/topics/extract-pdf",
                files={"file": ("guide.pdf", b"%PDF-1.4 minimal placeholder", "application/pdf")},
            )

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert len(events) == 1
    assert events[0]["stage"] == "error"
    assert events[0]["status_code"] == 504
