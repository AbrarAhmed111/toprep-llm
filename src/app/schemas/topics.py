"""
Pydantic Schemas for AI-Assisted Topic Organization.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class OrganizeTopicItem(BaseModel):
    """A single topic to be ordered."""
    id: str = Field(..., description="Client-side topic identifier")
    name: str = Field(..., description="Topic name/title")


class TopicOrganizeRequest(BaseModel):
    """Request payload for AI-assisted topic ordering."""
    preparation_title: str = Field(..., min_length=1, description="Title of the preparation")
    preparation_type: Optional[str] = Field(
        None, description="Preparation type: Interview, Exam, Certification, Custom"
    )
    topics: List[OrganizeTopicItem] = Field(
        ..., min_length=2, description="Topics to order (at least 2)"
    )


class TopicOrganizeResponse(BaseModel):
    """AI-suggested topic order. The caller must explicitly accept it before applying."""
    ordered_topic_ids: List[str] = Field(..., description="Topic IDs in the suggested learning order")
    reasoning: Optional[str] = Field(None, description="Short explanation of the suggested order")
    provider: str = Field(..., description="LLM provider that produced the suggestion")
    model: str = Field(..., description="Model name used")
