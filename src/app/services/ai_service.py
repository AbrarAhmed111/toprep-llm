"""
AI Features Service Layer.
Orchestrates:
1. Topic explanation generation
2. Expected questions generation
3. Multi-provider LLM Gateway invocation with automatic failover
"""

import logging
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage

from src.app.schemas.ai import (
    AIExplanationRequest,
    AIExplanationResponse,
    AIQuestionsRequest,
    AIQuestionsResponse,
)
from src.app.gateway import LLMGateway
from src.app.core.config import get_settings

logger = logging.getLogger("AIService")
settings = get_settings()

# Initialize the LLM Gateway instance
gateway = LLMGateway(
    max_attempts=settings.GATEWAY_MAX_ATTEMPTS,
    cooldown_seconds=settings.GATEWAY_COOLDOWN_SECONDS,
)


class AIService:
    """Service for AI-assisted topic features."""

    def __init__(self, gateway_instance: LLMGateway = gateway):
        self.gateway = gateway_instance

    async def generate_explanation(
        self, request: AIExplanationRequest
    ) -> AIExplanationResponse:
        """
        Generate a brief (2-3 line) explanation for a topic.

        Args:
            request: AIExplanationRequest with topic name and preparation context

        Returns:
            AIExplanationResponse with generated explanation
        """
        system_prompt = self._build_explanation_system_prompt()
        user_prompt = self._build_explanation_user_prompt(request)

        logger.info(
            f"📝 Generating explanation for topic: {request.topic_name} | "
            f"Prep type: {request.preparation_type or 'N/A'}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            logger.debug("🔄 Invoking LLM Gateway with automatic failover...")
            response_text, provider_name, model_name, usage, status_events = await self.gateway.invoke(
                messages=messages,
                temperature=0.7,
                max_tokens=150,
            )

            explanation = response_text.strip()

            logger.info(
                f"✅ Explanation generated successfully | "
                f"Provider: {provider_name} | Model: {model_name} | "
                f"Length: {len(explanation)} chars"
            )

            # Log status events (provider attempts, fallbacks)
            if status_events:
                for event in status_events:
                    if event.status == "fallback":
                        logger.warning(f"⚠️ Gateway fallback: {event.message}")
                    elif event.status == "switched":
                        logger.info(f"✅ Gateway switched: {event.message}")

            return AIExplanationResponse(
                explanation=explanation,
                provider=provider_name,
                model=model_name,
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to generate explanation for '{request.topic_name}': {type(e).__name__}: {str(e)}"
            )
            raise

    async def generate_questions(
        self, request: AIQuestionsRequest
    ) -> AIQuestionsResponse:
        """
        Generate expected interview/exam questions for a topic.

        Args:
            request: AIQuestionsRequest with topic name and preparation context

        Returns:
            AIQuestionsResponse with list of generated questions
        """
        system_prompt = self._build_questions_system_prompt()
        user_prompt = self._build_questions_user_prompt(request)

        logger.info(
            f"❓ Generating questions for topic: {request.topic_name} | "
            f"Prep type: {request.preparation_type or 'N/A'}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            logger.debug("🔄 Invoking LLM Gateway with automatic failover...")
            response_text, provider_name, model_name, usage, status_events = await self.gateway.invoke(
                messages=messages,
                temperature=0.8,
                max_tokens=300,
            )

            questions_text = response_text.strip()
            questions = self._parse_questions(questions_text)

            logger.info(
                f"✅ Generated {len(questions)} questions for '{request.topic_name}' | "
                f"Provider: {provider_name} | Model: {model_name}"
            )

            # Log status events (provider attempts, fallbacks)
            if status_events:
                for event in status_events:
                    if event.status == "fallback":
                        logger.warning(f"⚠️ Gateway fallback: {event.message}")
                    elif event.status == "switched":
                        logger.info(f"✅ Gateway switched: {event.message}")

            return AIQuestionsResponse(
                questions=questions,
                provider=provider_name,
                model=model_name,
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to generate questions for '{request.topic_name}': {type(e).__name__}: {str(e)}"
            )
            raise

    def _build_explanation_system_prompt(self) -> str:
        """Build system prompt for topic explanation generation."""
        return """You are an expert learning assistant. Your role is to generate clear, concise topic explanations.

Guidelines:
- Keep explanations to 2-3 lines maximum
- Focus on the core concept and its importance
- Use simple, beginner-friendly language
- Avoid jargon unless essential
- Make it relevant to learning/studying

Be direct and practical."""

    def _build_explanation_user_prompt(self, request: AIExplanationRequest) -> str:
        """Build user prompt for topic explanation generation."""
        prompt = f'Generate a brief explanation for the topic: "{request.topic_name}"'

        if request.preparation_type:
            prompt += f"\nPreparation type: {request.preparation_type}"

        if request.preparation_description:
            prompt += f"\nContext: {request.preparation_description}"

        prompt += "\n\nProvide ONLY the explanation, nothing else."
        return prompt

    def _build_questions_system_prompt(self) -> str:
        """Build system prompt for expected questions generation."""
        return """You are an expert interview/exam coach. Your role is to generate realistic, practical questions about topics.

Guidelines:
- Generate 3-5 focused, thoughtful questions
- Questions should test understanding, not just memorization
- Make questions realistic for the preparation type
- Each question should be clear and concise (1-2 lines)
- Order from basic to more advanced concepts
- Focus on what learners commonly struggle with

Format as a numbered list (1. 2. 3. etc)."""

    def _build_questions_user_prompt(self, request: AIQuestionsRequest) -> str:
        """Build user prompt for expected questions generation."""
        prompt = f'Generate expected questions for the topic: "{request.topic_name}"'

        if request.preparation_type and request.preparation_type.lower() != "custom":
            prompt += f"\nThis is for a {request.preparation_type} preparation"

        if request.preparation_description:
            prompt += f"\nContext: {request.preparation_description}"

        prompt += "\n\nProvide ONLY the numbered questions, nothing else."
        return prompt

    def _parse_questions(self, text: str) -> list[str]:
        """Parse numbered questions from LLM response."""
        lines = text.split("\n")
        questions = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match numbered format: "1. Question text" or "1) Question text"
            if line and line[0].isdigit():
                # Remove numbering
                cleaned = line.lstrip("0123456789.)) ")
                if cleaned:
                    questions.append(cleaned)
            elif line and not any(line.startswith(x) for x in ["*", "-", "#", "Note:", "etc"]):
                # Include other non-empty lines that aren't special markers
                if len(questions) < 5:  # Cap at 5 questions
                    questions.append(line)

        return questions[:5]  # Return max 5 questions


# Create a singleton instance
ai_service = AIService(gateway)
