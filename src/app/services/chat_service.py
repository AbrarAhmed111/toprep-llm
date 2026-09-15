"""
Chat Service Layer.
Orchestrates:
1. Intent detection (zero-LLM, offline rule-based)
2. Canned response dispatch for conversational shortcuts (0 tokens)
3. RAG retrieval over indexed knowledge documents
4. Grounded prompt assembly
5. Multi-provider LLM Gateway invocation with automatic failover
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
from src.app.intent import detect_intent, get_canned_response
from src.app.rag import RAGPipeline
from src.app.core.config import get_settings

logger = logging.getLogger("ChatService")
settings = get_settings()

# Initialize the LLM Gateway instance
gateway = LLMGateway(
    max_attempts=settings.GATEWAY_MAX_ATTEMPTS,
    cooldown_seconds=settings.GATEWAY_COOLDOWN_SECONDS,
)

# Initialize the RAG Pipeline
rag_pipeline = RAGPipeline(
    knowledge_dir=settings.resolved_knowledge_path,
    top_k=settings.RAG_TOP_K,
    chunk_size=settings.RAG_CHUNK_SIZE,
    chunk_overlap=settings.RAG_CHUNK_OVERLAP,
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
    """Service handling conversational intent routing, RAG retrieval, and LLM execution."""

    def __init__(self, gateway_instance: LLMGateway = gateway, rag_instance: RAGPipeline = rag_pipeline):
        self.gateway = gateway_instance
        self.rag = rag_instance

    def get_fast_prompts(self) -> FastPromptsResponse:
        """Returns product-focused fast prompt suggestions for the chatbot UI."""
        return FastPromptsResponse(prompts=DEFAULT_FAST_PROMPTS)

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process incoming chat messages:
        - Filters out empty messages.
        - Extracts latest user message.
        - Evaluates intent.
        - Returns canned answer if conversational.
        - Otherwise retrieves RAG context and routes through the LLM gateway.
        """
        clean_messages = [m for m in request.messages if m.content and m.content.strip()]
        if not clean_messages:
            clean_messages = [ChatMessage(role="user", content="Hello")]

        latest_user_content = next(
            (m.content for m in reversed(clean_messages) if m.role == "user"),
            clean_messages[-1].content,
        )

        logger.info(f"📨 Incoming Query: \"{latest_user_content}\"")

        # 1. Intent Detection (Zero LLM, Zero Cost)
        intent_result = detect_intent(latest_user_content)

        if not intent_result.should_use_llm:
            logger.info(
                f"⚡ [INTENT DETECTED: '{intent_result.intent}'] (Confidence: {intent_result.confidence:.2f}) "
                f"-> Used: [LOCAL CANNED TEXT] | Cloud Model: NONE (0 Tokens consumed)"
            )
            canned_reply = get_canned_response(intent_result.intent)
            return ChatResponse(
                reply=canned_reply,
                provider="canned_response",
                model="rule_based",
                usage=UsageInfo(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                intent=intent_result.intent,
                sources=[],
                status_events=[],
            )

        # 2. Substantive Query -> RAG Retrieval & Prompt Grounding
        logger.info(
            f"🔍 [INTENT DETECTED: '{intent_result.intent}'] -> Performing RAG Retrieval over Knowledge Base..."
        )
        system_prompt_with_context, retrieved_sources = self.rag.build_prompt_context(
            query=latest_user_content
        )

        logger.info(
            f"☁️ Routing to Cloud LLM Gateway across configured providers (Sources: {retrieved_sources})..."
        )

        # Build message history with grounded system instructions
        langchain_messages: List[BaseMessage] = [SystemMessage(content=system_prompt_with_context)]
        for m in clean_messages:
            if m.role != "system":  # Replace existing system message with grounded RAG context
                langchain_messages.append(to_langchain_message(m))

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
            intent=intent_result.intent,
            sources=retrieved_sources,
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
