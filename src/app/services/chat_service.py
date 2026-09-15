"""
Chat Service Layer.
Orchestrates:
1. Chat message normalization
2. Multi-provider LLM Gateway invocation with automatic failover
"""

import logging
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from src.app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    UsageInfo,
    ProviderStatusEventSchema,
    FastPrompt,
    FastPromptsResponse,
)
from src.app.gateway import LLMGateway
from src.app.core.config import get_settings

logger = logging.getLogger("ChatService")
settings = get_settings()

# Initialize the LLM Gateway instance
gateway = LLMGateway(
    max_attempts=settings.GATEWAY_MAX_ATTEMPTS,
    cooldown_seconds=settings.GATEWAY_COOLDOWN_SECONDS,
)


# Generic Starter Fast Prompts for Chatbot UI
DEFAULT_FAST_PROMPTS: List[FastPrompt] = [
    FastPrompt(
        label="Platform Overview",
        prompt="What is this platform and what are its key capabilities?",
        category="General",
    ),
    FastPrompt(
        label="API Authentication",
        prompt="How do I authenticate HTTP requests to the API?",
        category="Technical",
    ),
    FastPrompt(
        label="Subscription Tiers",
        prompt="What subscription plans and pricing tiers are available?",
        category="Billing",
    ),
    FastPrompt(
        label="Rate Limiting",
        prompt="What are the API rate limits and how does the system handle 429 errors?",
        category="Technical",
    ),
    FastPrompt(
        label="Webhook Alerts",
        prompt="How do I configure webhook alerts for monitoring?",
        category="Technical",
    ),
]


def to_langchain_message(msg: ChatMessage) -> BaseMessage:
    """Map ChatMessage schema to LangChain message abstractions."""
    if msg.role == "system":
        return SystemMessage(content=msg.content)
    elif msg.role == "assistant":
        return AIMessage(content=msg.content)
    else:
        return HumanMessage(content=msg.content)


class ChatService:
    """Service handling chat message normalization and LLM execution."""

    def __init__(self, gateway_instance: LLMGateway = gateway):
        self.gateway = gateway_instance

    def get_fast_prompts(self) -> FastPromptsResponse:
        """Returns product-focused fast prompt suggestions for the chatbot UI."""
        return FastPromptsResponse(prompts=DEFAULT_FAST_PROMPTS)

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process incoming chat messages:
        - Filters out empty messages.
        - Routes the conversation through the LLM gateway with failover.
        """
        clean_messages = [m for m in request.messages if m.content and m.content.strip()]
        if not clean_messages:
            clean_messages = [ChatMessage(role="user", content="Hello")]

        latest_user_content = next(
            (m.content for m in reversed(clean_messages) if m.role == "user"),
            clean_messages[-1].content,
        )

        logger.info(f"📨 Incoming Query: \"{latest_user_content}\"")
        logger.info("☁️ Routing to Cloud LLM Gateway across configured providers...")

        langchain_messages: List[BaseMessage] = [to_langchain_message(m) for m in clean_messages]

        reply, provider_name, model_name, usage, status_events = await self.gateway.generate(
            messages=langchain_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        logger.info(
            f"✅ [CLOUD MODEL COMPLETED] Provider: {provider_name} | Model: {model_name} "
            f"| Total Tokens: {usage.get('total_tokens', 0)} (Prompt: {usage.get('prompt_tokens', 0)}, Completion: {usage.get('completion_tokens', 0)})"
        )

        return ChatResponse(
            reply=reply,
            provider=provider_name,
            model=model_name,
            usage=UsageInfo(**usage),
            status_events=[
                ProviderStatusEventSchema(
                    type=ev.type,
                    status=ev.status,
                    message=ev.message,
                    provider=ev.provider,
                )
                for ev in status_events
            ],
        )


# Singleton instance
chat_service = ChatService()
