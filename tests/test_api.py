"""
API Integration Tests for LLM RAG Starter.
Tests /health, /api/chat, /api/chat/fast-prompts, and CORS headers.
Completely mocked (zero tokens consumed).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

from src.app.main import app
from src.app.gateway import ProviderStatusEvent


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_root():
    """Test root endpoint returns service info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data


@pytest.mark.asyncio
async def test_health():
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "rag_index" in data
        assert "gateway" in data


@pytest.mark.asyncio
async def test_get_fast_prompts():
    """Test GET /api/chat/fast-prompts endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/chat/fast-prompts")
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert len(data["prompts"]) >= 3
        for p in data["prompts"]:
            assert "label" in p
            assert "prompt" in p
            assert "category" in p


@pytest.mark.asyncio
async def test_chat_conversational_canned():
    """Test POST /api/chat with conversational greeting bypasses LLM (0 tokens)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"messages": [{"role": "user", "content": "Hello!"}]}
        response = await client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "canned_response"
        assert data["intent"] == "greeting"
        assert data["usage"]["total_tokens"] == 0
        assert len(data["reply"]) > 5


@pytest.mark.asyncio
async def test_chat_domain_query_via_gateway():
    """Test POST /api/chat with technical query retrieves context and routes to gateway."""
    mock_return = (
        "Apex Cloud API requests are authenticated by passing your API key in the Authorization header.",
        "Primary Mock Provider",
        "mock-model",
        {"prompt_tokens": 40, "completion_tokens": 20, "total_tokens": 60},
        [],
    )

    with patch("app.services.chat_service.gateway.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_return

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {"messages": [{"role": "user", "content": "How do I authenticate API requests?"}]}
            response = await client.post("/api/chat", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "Primary Mock Provider"
            assert data["model"] == "mock-model"
            assert data["usage"]["total_tokens"] == 60
            assert len(data["sources"]) >= 1
            mock_gen.assert_called_once()
