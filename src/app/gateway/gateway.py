"""
LLM Gateway Layer.
Provides automatic fallback across multiple providers and multiple API keys.

Handles:
- Deployments configuration (Gemini x4, Groq, OpenAI, Mistral, Cerebras)
- Error classification (retryable 429/quota/5xx vs non-retryable 400/401)
- Cooldown tracking (avoids hammering a provider that recently rate-limited)
- User-facing provider status events ("fallback", "switched")
- Normalized token usage metrics
"""

import time
import logging
from typing import List, Optional, Tuple, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from .deployment import ProviderDeployment
from .error_classifier import ErrorClassifier
from .status import ProviderStatusEvent
from src.app.core.config import get_settings

logger = logging.getLogger("LLMGateway")


class LLMGateway:
    """
    Manages provider deployments, ordered fallback, and status events.
    Decouples the application layer from specific LLM providers.
    """

    def __init__(self, max_attempts: int = 10, cooldown_seconds: int = 60):
        self.max_attempts = max_attempts
        self.cooldown_seconds = cooldown_seconds
        self.deployments: List[ProviderDeployment] = []
        self._load_deployments_from_config()

    def _load_deployments_from_config(self) -> None:
        """
        Dynamically loads configured provider deployments from settings.
        Supported providers:
        - Gemini: GOOGLE_API_KEY1..4
        - Groq: GROQ_API_KEY
        - OpenAI: OPENAI_API_KEY
        - Mistral: MISTRAL_API_KEY
        - Cerebras: CEREBRAS_API_KEY
        """
        settings = get_settings()
        gemini_base = "https://generativelanguage.googleapis.com/v1beta/openai/"

        # 1. Google Gemini Deployments (Supports up to 4 rotated keys)
        for i in range(1, 5):
            key = getattr(settings, f"GOOGLE_API_KEY{i}", "")
            if key and key.strip():
                self.deployments.append(
                    ProviderDeployment(
                        name=f"Gemini #{i}",
                        provider="gemini",
                        api_key=key.strip(),
                        base_url=gemini_base,
                        default_model=settings.GEMINI_MODEL,
                        cooldown_seconds=self.cooldown_seconds,
                    )
                )

        # Gemini Quality Fallback (uses Primary Key if configured)
        if settings.GOOGLE_API_KEY1 and settings.GOOGLE_API_KEY1.strip() and settings.GEMINI_FALLBACK_MODEL:
            self.deployments.append(
                ProviderDeployment(
                    name="Gemini (Quality Fallback)",
                    provider="gemini",
                    api_key=settings.GOOGLE_API_KEY1.strip(),
                    base_url=gemini_base,
                    default_model=settings.GEMINI_FALLBACK_MODEL,
                    cooldown_seconds=self.cooldown_seconds,
                )
            )

        # 2. Groq Deployments (Primary + Fallback)
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
            self.deployments.append(
                ProviderDeployment(
                    name="Groq",
                    provider="groq",
                    api_key=settings.GROQ_API_KEY.strip(),
                    base_url="https://api.groq.com/openai/v1",
                    default_model=settings.GROQ_MODEL,
                    cooldown_seconds=self.cooldown_seconds,
                )
            )
            if settings.GROQ_FALLBACK_MODEL:
                self.deployments.append(
                    ProviderDeployment(
                        name="Groq (Quality Fallback)",
                        provider="groq",
                        api_key=settings.GROQ_API_KEY.strip(),
                        base_url="https://api.groq.com/openai/v1",
                        default_model=settings.GROQ_FALLBACK_MODEL,
                        cooldown_seconds=self.cooldown_seconds,
                    )
                )

        # 3. OpenAI Deployment
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            self.deployments.append(
                ProviderDeployment(
                    name="OpenAI",
                    provider="openai",
                    api_key=settings.OPENAI_API_KEY.strip(),
                    base_url=None,  # Standard OpenAI default
                    default_model=settings.OPENAI_MODEL,
                    cooldown_seconds=self.cooldown_seconds,
                )
            )

        # 4. Mistral Deployment
        if settings.MISTRAL_API_KEY and settings.MISTRAL_API_KEY.strip():
            self.deployments.append(
                ProviderDeployment(
                    name="Mistral",
                    provider="mistral",
                    api_key=settings.MISTRAL_API_KEY.strip(),
                    base_url="https://api.mistral.ai/v1",
                    default_model=settings.MISTRAL_MODEL,
                    cooldown_seconds=self.cooldown_seconds,
                )
            )

        # 5. Cerebras Deployment
        if settings.CEREBRAS_API_KEY and settings.CEREBRAS_API_KEY.strip():
            self.deployments.append(
                ProviderDeployment(
                    name="Cerebras",
                    provider="cerebras",
                    api_key=settings.CEREBRAS_API_KEY.strip(),
                    base_url="https://api.cerebras.ai/v1",
                    default_model=settings.CEREBRAS_MODEL,
                    cooldown_seconds=self.cooldown_seconds,
                )
            )

    def get_available_deployments(self) -> List[ProviderDeployment]:
        """Returns deployments that are configured and not in cooldown."""
        return [d for d in self.deployments if d.is_available]

    async def generate(
        self,
        messages: List[BaseMessage],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, str, str, Dict[str, int], List[ProviderStatusEvent]]:
        """
        Executes chat completion with automatic fallback across providers.

        Returns:
            (reply, provider_name, model_name, usage_dict, status_events)
        """
        available = self.get_available_deployments()

        # If all active deployments are cooling down, attempt the one cooling down the soonest
        if not available:
            active = [d for d in self.deployments if not d.is_permanently_disabled]
            if not active:
                raise RuntimeError("No LLM provider deployments configured or available.")
            active.sort(key=lambda d: d.cooldown_until)
            available = [active[0]]

        status_events: List[ProviderStatusEvent] = []
        attempts = 0
        last_error = None

        for deployment in available:
            if attempts >= self.max_attempts:
                break

            attempts += 1

            try:
                logger.info(
                    f"🌐 Connecting to Cloud LLM Provider: {deployment.name} ({deployment.default_model}) "
                    f"[Attempt {attempts}/{self.max_attempts}]..."
                )
                llm = ChatOpenAI(
                    api_key=deployment.api_key,
                    base_url=deployment.base_url,
                    model=deployment.default_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30.0,
                )

                # Invoke the model asynchronously
                start_time = time.time()
                ai_response = await llm.ainvoke(messages)
                duration_ms = int((time.time() - start_time) * 1000)

                # If we had previous fallbacks, emit a "switched" event
                if len(status_events) > 0:
                    status_events.append(
                        ProviderStatusEvent(
                            type="provider_status",
                            status="switched",
                            message=f"Switched to {deployment.name} successfully.",
                            provider=deployment.name,
                        )
                    )

                # Normalize usage metadata
                usage_metadata = getattr(ai_response, "usage_metadata", None) or {}
                usage = {
                    "prompt_tokens": usage_metadata.get("input_tokens", 0),
                    "completion_tokens": usage_metadata.get("output_tokens", 0),
                    "total_tokens": usage_metadata.get("total_tokens", 0),
                }

                logger.info(
                    f"✅ LLM Call Succeeded via {deployment.name} in {duration_ms}ms | "
                    f"Tokens: {usage['prompt_tokens']} in, {usage['completion_tokens']} out ({usage['total_tokens']} total)"
                )

                reply_content = ai_response.content
                if isinstance(reply_content, list):
                    reply_content = "".join(
                        str(part.get("text", "")) if isinstance(part, dict) else str(part)
                        for part in reply_content
                    )

                return (
                    str(reply_content),
                    deployment.name,
                    deployment.default_model,
                    usage,
                    status_events,
                )

            except Exception as e:
                last_error = e
                is_retryable, reason = ErrorClassifier.is_retryable(e)

                if is_retryable:
                    if reason == "model_or_endpoint_not_found":
                        deployment.mark_disabled()
                        msg = f"{deployment.name} model '{deployment.default_model}' is unavailable. Switching to another provider..."
                        status_events.append(
                            ProviderStatusEvent(
                                type="provider_status",
                                status="fallback",
                                message=msg,
                                provider=deployment.name,
                            )
                        )
                        logger.warning(
                            f"⚠️ Fallback triggered for {deployment.name}: model '{deployment.default_model}' not found (404). "
                            f"Disabling and switching to next provider..."
                        )
                        continue
                    else:
                        # Put failed deployment on cooldown
                        deployment.mark_cooldown(self.cooldown_seconds)
                        msg = f"{deployment.name} has reached its API limit or is unavailable. Switching to another provider..."
                        status_events.append(
                            ProviderStatusEvent(
                                type="provider_status",
                                status="fallback",
                                message=msg,
                                provider=deployment.name,
                            )
                        )
                        logger.warning(f"⚠️ Fallback triggered for {deployment.name}: {reason} ({str(e)})")
                        continue
                else:
                    # Non-retryable error on this specific provider (e.g. invalid key)
                    if reason == "invalid_api_key":
                        deployment.mark_disabled()
                        logger.error(f"⚠️ Permanently disabling {deployment.name} due to invalid API key. Falling back to next provider...")
                        status_events.append(
                            ProviderStatusEvent(
                                type="provider_status",
                                status="fallback",
                                message=f"{deployment.name} authentication failed. Switching to another provider...",
                                provider=deployment.name,
                            )
                        )
                        continue
                    raise e

        # If all attempts exhausted
        logger.error(f"❌ All LLM provider attempts failed after {attempts} attempts. Last error: {str(last_error)}")
        raise RuntimeError(
            f"All LLM providers are currently unavailable or in cooldown. Last error: {str(last_error)}"
        )
