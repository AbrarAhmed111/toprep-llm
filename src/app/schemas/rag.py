"""
Pydantic Schemas for RAG Document Ingestion, Chunking, and Retrieval.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Represents a text chunk extracted from a source document."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    source: str = Field(..., description="Source document path or filename")
    title: str = Field(default="", description="Section or document title")
    content: str = Field(..., description="Chunk text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional arbitrary metadata")


class RetrievalResult(BaseModel):
    """Represents the outcome of a vector/hybrid retrieval query."""
    query: str = Field(..., description="The search query evaluated")
    chunks: List[DocumentChunk] = Field(default_factory=list, description="Retrieved chunks ordered by relevance")
    scores: List[float] = Field(default_factory=list, description="Similarity or relevance scores")
    has_relevant_context: bool = Field(default=False, description="True if at least one chunk exceeds score threshold")
