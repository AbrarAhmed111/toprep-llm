"""
API-level tests for POST /api/topics/extract-pdf.
Completely mocked LLM calls (patched on the shared chat_service.gateway
singleton) -- verifies the endpoint contract the frontend already relies on
(pdfExtraction.ts): multipart `file` in, `{"topics": [...]}` out, and
user-readable error details rather than raw 500s for bad input.
"""

import asyncio
import json
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


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_returns_deduplicated_topics():
    pdf_bytes = _build_pdf_bytes(
        [
            "React Hooks let you use state in function components.",
            "Promises represent the eventual completion of an async operation.",
        ]
    )
    extraction_reply = json.dumps({"topics": ["React Hooks", "JavaScript Promises"]})
    normalization_reply = json.dumps(
        {
            "groups": [
                {"name": "React Hooks", "indices": [0]},
                {"name": "JavaScript Promises", "indices": [1]},
            ]
        }
    )

    with patch.object(
        gateway,
        "generate",
        new=AsyncMock(
            side_effect=[
                (extraction_reply, "Groq", "test-model", {}, []),
                (normalization_reply, "Groq", "test-model", {}, []),
            ]
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/topics/extract-pdf",
                files={"file": ("guide.pdf", pdf_bytes, "application/pdf")},
            )

    assert response.status_code == 200
    assert response.json() == {"topics": ["React Hooks", "JavaScript Promises"]}


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
async def test_extract_pdf_endpoint_returns_readable_error_for_corrupt_pdf():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/topics/extract-pdf",
            files={"file": ("guide.pdf", b"this is not really a pdf", "application/pdf")},
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "could not be processed" in detail.lower()
    assert "Traceback" not in detail


@pytest.mark.asyncio
async def test_extract_pdf_endpoint_times_out_on_slow_pipeline(monkeypatch):
    monkeypatch.setattr(get_settings(), "PDF_PIPELINE_TIMEOUT_SECONDS", 0.05)

    async def _slow_pipeline(_file_bytes):
        await asyncio.sleep(0.3)
        return ["Should never be reached"]

    with patch("src.app.api.routes.topics.extract_topics_from_pdf", new=_slow_pipeline):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/topics/extract-pdf",
                files={"file": ("guide.pdf", b"%PDF-1.4 minimal placeholder", "application/pdf")},
            )

    assert response.status_code == 504
