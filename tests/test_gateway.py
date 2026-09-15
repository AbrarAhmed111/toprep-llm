"""
Unit tests for Multi-Provider LLM Gateway.
Tests primary success, 429 quota fallback, 404 model not found fallback, cooldowns, and exhausted failover.
Completely mocked (0 real API tokens consumed).
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage

from src.app.gateway import LLMGateway, ProviderDeployment, ErrorClassifier


@pytest.fixture
def mock_gateway():
    """Returns an LLMGateway with two synthetic provider deployments."""
    gw = LLMGateway(max_attempts=5, cooldown_seconds=60)
    gw.deployments = [
        ProviderDeployment(
            name="Primary Mock Provider",
            provider="mock_primary",
            api_key="test-key-1",
            base_url="https://mock.primary.ai/v1",
            default_model="mock-fast-model",
            cooldown_seconds=60,
        ),
        ProviderDeployment(
            name="Fallback Mock Provider",
            provider="mock_fallback",
            api_key="test-key-2",
            base_url="https://mock.fallback.ai/v1",
            default_model="mock-fallback-model",
            cooldown_seconds=60,
        ),
    ]
    return gw


@pytest.mark.asyncio
async def test_gateway_primary_success(mock_gateway):
    """Verify successful response on the primary deployment."""
    mock_ai_resp = AIMessage(
        content="This is a successful mock response.",
        usage_metadata={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18},
    )

    with patch("app.gateway.gateway.ChatOpenAI") as mock_chat_cls:
        instance = MagicMock()
        instance.ainvoke = AsyncMock(return_value=mock_ai_resp)
        mock_chat_cls.return_value = instance

        messages = [HumanMessage(content="Hello")]
        reply, provider, model, usage, status_events = await mock_gateway.generate(messages)

        assert reply == "This is a successful mock response."
        assert provider == "Primary Mock Provider"
        assert model == "mock-fast-model"
        assert usage["total_tokens"] == 18
        assert len(status_events) == 0


@pytest.mark.asyncio
async def test_gateway_fallback_on_429_rate_limit(mock_gateway):
    """Verify gateway falls back to secondary provider on 429 rate limit."""
    mock_ai_resp = AIMessage(
        content="Fallback response after 429.",
        usage_metadata={"input_tokens": 12, "output_tokens": 5, "total_tokens": 17},
    )

    with patch("app.gateway.gateway.ChatOpenAI") as mock_chat_cls:
        primary_inst = MagicMock()
        primary_inst.ainvoke = AsyncMock(side_effect=Exception("Error code: 429 - Rate limit reached or quota exceeded"))

        fallback_inst = MagicMock()
        fallback_inst.ainvoke = AsyncMock(return_value=mock_ai_resp)

        mock_chat_cls.side_effect = [primary_inst, fallback_inst]

        messages = [HumanMessage(content="Test query")]
        reply, provider, model, usage, status_events = await mock_gateway.generate(messages)

        assert reply == "Fallback response after 429."
        assert provider == "Fallback Mock Provider"
        assert model == "mock-fallback-model"
        assert len(status_events) >= 1
        assert any(e.status == "fallback" for e in status_events)
        assert not mock_gateway.deployments[0].is_available


@pytest.mark.asyncio
async def test_gateway_fallback_on_404_model_not_found(mock_gateway):
    """Verify gateway permanently disables a 404 deployment and recovers via fallback."""
    mock_ai_resp = AIMessage(
        content="Fallback response after 404.",
        usage_metadata={"input_tokens": 10, "output_tokens": 6, "total_tokens": 16},
    )

    with patch("app.gateway.gateway.ChatOpenAI") as mock_chat_cls:
        primary_inst = MagicMock()
        primary_inst.ainvoke = AsyncMock(side_effect=Exception("Error code: 404 - The model mock-fast-model is not found"))

        fallback_inst = MagicMock()
        fallback_inst.ainvoke = AsyncMock(return_value=mock_ai_resp)

        mock_chat_cls.side_effect = [primary_inst, fallback_inst]

        messages = [HumanMessage(content="Test 404 query")]
        reply, provider, model, usage, status_events = await mock_gateway.generate(messages)

        assert reply == "Fallback response after 404."
        assert provider == "Fallback Mock Provider"
        assert mock_gateway.deployments[0].is_permanently_disabled is True


@pytest.mark.asyncio
async def test_gateway_all_deployments_failed(mock_gateway):
    """Verify gateway raises a clean RuntimeError when all providers fail."""
    with patch("app.gateway.gateway.ChatOpenAI") as mock_chat_cls:
        fail_inst = MagicMock()
        fail_inst.ainvoke = AsyncMock(side_effect=Exception("Error code: 503 - Service Unavailable"))
        mock_chat_cls.return_value = fail_inst

        messages = [HumanMessage(content="Query to failing gateway")]
        with pytest.raises(RuntimeError, match="All LLM providers are currently unavailable"):
            await mock_gateway.generate(messages)
