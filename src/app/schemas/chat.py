"""
Pydantic Schemas for Chatbot & LLM Gateway interactions.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Represents a single message in conversation history."""
    role: str = Field(default="user", description="Sender role: user, assistant, or system")
    content: str = Field(default="", description="Message text content")


class ChatRequest(BaseModel):
    """Request payload from client."""
    messages: List[ChatMessage] = Field(..., min_length=1, description="Conversation messages")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Creativity temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Max tokens to generate")


class ProviderStatusEventSchema(BaseModel):
    """Structured status event emitted when a provider switches or fails over."""
    type: str = "provider_status"
    status: str = Field(..., description="Event status: 'fallback' or 'switched'")
    message: str = Field(..., description="User-facing status message")
    provider: str = Field(..., description="Name of the provider deployment")


class UsageInfo(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """Chat completion response including answer, provider info, detected intent, and status events."""
    reply: str = Field(..., description="The assistant or canned response text")
    provider: str = Field(..., description="Provider that fulfilled the request")
    model: str = Field(..., description="Model name or rule identifier")
    usage: UsageInfo = Field(default_factory=UsageInfo, description="Token consumption metrics")
    intent: Optional[str] = Field(None, description="Detected user intent")
    sources: List[str] = Field(default_factory=list, description="Retrieved document sources")
    status_events: List[ProviderStatusEventSchema] = Field(
        default_factory=list,
        description="Failover or provider status event history",
    )


class FastPrompt(BaseModel):
    """Suggested quick action / fast prompt button for the chatbot UI."""
    label: str = Field(..., description="Short button text")
    prompt: str = Field(..., description="Full prompt text sent when clicked")
    category: str = Field(default="General", description="Topic category")


class FastPromptsResponse(BaseModel):
    """List of product-focused fast prompt suggestions."""
    prompts: List[FastPrompt]
