"""
Unit tests for the RAG Engine.
Tests markdown chunking, document loading, similarity retrieval, and prompt context formatting.
"""

import os
import pytest
from src.app.rag.chunking.text_splitter import MarkdownTextSplitter
from src.app.rag.ingestion.loader import DocumentLoader
from src.app.rag.retrieval.vector_store import InMemoryHybridVectorStore
from src.app.rag.context.builder import ContextBuilder
from src.app.rag.pipeline import RAGPipeline
from src.app.schemas.rag import DocumentChunk


SAMPLE_MARKDOWN = """# Platform Guide

## Authentication
To authenticate requests, include the API key in the Authorization header as Bearer token.

## Pricing Plans
Starter plan is free forever. Growth plan is $29/month with 10 concurrent workers.
"""


def test_markdown_text_splitter():
    """Verify markdown splitter preserves sections and headers."""
    splitter = MarkdownTextSplitter(chunk_size=200, chunk_overlap=20)
    chunks = splitter.split_document(SAMPLE_MARKDOWN, source="sample.md")

    assert len(chunks) >= 2
    titles = [c.title for c in chunks]
    assert any("Authentication" in t for t in titles)
    assert any("Pricing Plans" in t for t in titles)
    for c in chunks:
        assert c.source == "sample.md"
        assert len(c.content) > 0


def test_in_memory_vector_store_retrieval():
    """Verify BM25 retrieval finds relevant chunks and orders by score."""
    store = InMemoryHybridVectorStore()
    chunks = [
        DocumentChunk(
            chunk_id="1",
            source="auth.md",
            title="Authentication",
            content="API keys must be passed in the Authorization header as Bearer tokens.",
        ),
        DocumentChunk(
            chunk_id="2",
            source="pricing.md",
            title="Pricing",
            content="Starter plan is free. Growth plan costs $29 per month.",
        ),
    ]
    store.add_chunks(chunks)

    # Search for auth query
    result_auth = store.search(query="How do I pass my API key in Authorization header?", top_k=2)
    assert len(result_auth.chunks) >= 1
    assert result_auth.chunks[0].title == "Authentication"
    assert result_auth.has_relevant_context is True

    # Search for pricing query
    result_pricing = store.search(query="What is the price of the Growth plan?", top_k=2)
    assert len(result_pricing.chunks) >= 1
    assert result_pricing.chunks[0].title == "Pricing"


def test_context_builder_formatting():
    """Verify context builder outputs formatted markdown and system instructions."""
    store = InMemoryHybridVectorStore()
    chunk = DocumentChunk(
        chunk_id="chunk-1",
        source="guide.md",
        title="Serverless Compute",
        content="Deploy stateless functions with sub-50ms cold starts.",
    )
    store.add_chunks([chunk])

    retrieval_res = store.search(query="serverless compute functions", top_k=1)
    context_block = ContextBuilder.format_context_block(retrieval_res)

    assert "[RETRIEVED DOCUMENTATION CONTEXT]" in context_block
    assert "[guide.md]" in context_block
    assert "Serverless Compute" in context_block
    assert "Deploy stateless functions" in context_block


def test_rag_pipeline_end_to_end():
    """Verify RAG pipeline loads knowledge documents and builds prompt context."""
    from src.app.core.config import get_settings
    settings = get_settings()

    pipeline = RAGPipeline(
        knowledge_dir=settings.resolved_knowledge_path,
        top_k=2,
        chunk_size=400,
        chunk_overlap=50,
    )
    pipeline.initialize()
    assert pipeline.is_initialized is True

    prompt, sources = pipeline.build_prompt_context("How do I authenticate API requests?")
    assert "AI Knowledge Assistant" in prompt
    assert "[RETRIEVED DOCUMENTATION CONTEXT]" in prompt
    assert len(sources) >= 1

