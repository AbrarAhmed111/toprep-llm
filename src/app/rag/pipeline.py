"""
Unified RAG Pipeline Orchestrator.
Combines document loading, chunking, indexing, retrieval, and prompt context formatting.
"""

import logging
from typing import List, Tuple
from src.app.core.config import get_settings
from src.app.schemas.rag import RetrievalResult
from src.app.rag.ingestion.loader import DocumentLoader
from src.app.rag.retrieval.vector_store import InMemoryHybridVectorStore, BaseVectorStore
from src.app.rag.context.builder import ContextBuilder

logger = logging.getLogger("RAGPipeline")


class RAGPipeline:
    """End-to-end RAG orchestrator for document indexing and context assembly."""

    def __init__(
        self,
        knowledge_dir: str = "knowledge/documents",
        vector_store: BaseVectorStore = None,
        top_k: int = 3,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
    ):
        self.knowledge_dir = knowledge_dir
        self.top_k = top_k
        self.vector_store = vector_store or InMemoryHybridVectorStore()
        self.loader = DocumentLoader(
            directory_path=knowledge_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.is_initialized = False

    def initialize(self) -> None:
        """Loads and indexes knowledge documents on application startup."""
        logger.info(f"🔄 Initializing RAG Pipeline from '{self.knowledge_dir}'...")
        chunks = self.loader.load_documents()
        if chunks:
            self.vector_store.add_chunks(chunks)
        self.is_initialized = True
        logger.info(f"✅ RAG Pipeline Initialized with {len(chunks)} chunks indexed.")

    def retrieve(self, query: str, top_k: int = None) -> RetrievalResult:
        """Executes similarity retrieval for a given query."""
        if not self.is_initialized:
            self.initialize()
        k = top_k or self.top_k
        return self.vector_store.search(query=query, top_k=k)

    def build_prompt_context(self, query: str, top_k: int = None) -> Tuple[str, List[str]]:
        """
        Retrieves relevant context for query and builds a full grounded system prompt.

        Returns:
            Tuple of (full_system_prompt_with_context, list_of_unique_source_files)
        """
        settings = get_settings()
        retrieval_result = self.retrieve(query=query, top_k=top_k)

        base_system_prompt = ContextBuilder.build_system_prompt(
            assistant_name=settings.ASSISTANT_NAME
        )
        context_block = ContextBuilder.format_context_block(retrieval_result)
        full_system_prompt = f"{base_system_prompt}\n\n{context_block}"

        unique_sources = list(dict.fromkeys(chunk.source for chunk in retrieval_result.chunks))
        return full_system_prompt, unique_sources
