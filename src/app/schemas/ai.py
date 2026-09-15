"""
Pydantic Schemas for AI-Assisted Topic Features.
Explanations and expected questions generation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AIExplanationRequest(BaseModel):
    """Request for generating a topic explanation."""
    topic_name: str = Field(..., min_length=1, description="Topic name to explain")
    preparation_type: Optional[str] = Field(
        None, description="Preparation type: Interview, Exam, Certification, Custom"
    )
    preparation_description: Optional[str] = Field(
        None, description="Preparation description for context"
    )


class AIExplanationResponse(BaseModel):
    """AI-generated topic explanation response."""
    explanation: str = Field(..., description="Brief 2-3 line explanation of the topic")
    provider: str = Field(..., description="LLM provider that generated the explanation")
    model: str = Field(..., description="Model name used")


class AIQuestionsRequest(BaseModel):
    """Request for generating expected questions."""
    topic_name: str = Field(..., min_length=1, description="Topic name")
    preparation_type: Optional[str] = Field(
        None, description="Preparation type: Interview, Exam, Certification, Custom"
    )
    preparation_description: Optional[str] = Field(
        None, description="Preparation description for context"
    )


class AIQuestionsResponse(BaseModel):
    """AI-generated expected questions response."""
    questions: List[str] = Field(..., description="List of 3-5 expected questions")
    provider: str = Field(..., description="LLM provider that generated the questions")
    model: str = Field(..., description="Model name used")
