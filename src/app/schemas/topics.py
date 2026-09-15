"""
Pydantic Schemas for AI-Assisted Topic Organization.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class OrganizeTopicItem(BaseModel):
    """A single topic to be ordered."""
    id: str = Field(..., description="Client-side topic identifier")
    name: str = Field(..., description="Topic name/title")


class OrganizeSectionItem(BaseModel):
    """An existing section the AI may reuse when grouping topics."""
    id: str = Field(..., description="Client-side section identifier")
    name: str = Field(..., description="Section name")


class TopicOrganizeRequest(BaseModel):
    """Request payload for AI-assisted topic ordering and grouping."""
    preparation_title: str = Field(..., min_length=1, description="Title of the preparation")
    preparation_type: Optional[str] = Field(
        None, description="Preparation type: Interview, Exam, Certification, Custom"
    )
    topics: List[OrganizeTopicItem] = Field(
        ..., min_length=2, description="Topics to order (at least 2)"
    )
    sections: List[OrganizeSectionItem] = Field(
        default_factory=list, description="Existing sections the AI may reuse"
    )


class TopicSectionAssignment(BaseModel):
    """The section a topic should belong to, by name."""
    topic_id: str = Field(..., description="Topic ID this assignment applies to")
    section_name: Optional[str] = Field(
        None,
        description=(
            "Section name for this topic — either an existing section name "
            "(reused as-is) or a new one to create. Null/omitted leaves the "
            "topic unsectioned."
        ),
    )


class TopicOrganizeResponse(BaseModel):
    """AI-suggested topic order and section grouping, applied immediately by the caller."""
    ordered_topic_ids: List[str] = Field(..., description="Topic IDs in the suggested learning order")
    section_assignments: List[TopicSectionAssignment] = Field(
        default_factory=list,
        description="Suggested section for each topic, one entry per input topic",
    )
    reasoning: Optional[str] = Field(None, description="Short explanation of the suggested order")
    provider: str = Field(..., description="LLM provider that produced the suggestion")
    model: str = Field(..., description="Model name used")
