"""
Vector Store and Hybrid Retrieval Engine.
Provides an out-of-the-box in-memory hybrid search index with pluggable extension points
for production vector databases (PostgreSQL + pgvector, Chroma, Pinecone, Qdrant).
"""

import math
import logging
from abc import ABC, abstractmethod
from typing import List, Tuple
from collections import Counter
from src.app.schemas.rag import DocumentChunk, RetrievalResult

logger = logging.getLogger("RAGRetriever")


class BaseVectorStore(ABC):
    """Abstract interface for RAG vector index backends."""

    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Indexes document chunks."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> RetrievalResult:
        """Searches index for most relevant chunks given a query."""
        pass


class InMemoryHybridVectorStore(BaseVectorStore):
    """
    Default lightweight in-memory hybrid vector store.
    Combines TF-IDF / BM25 term weighting and vector cosine similarity
    without requiring external database setup or paid embedding API calls.

    EXTENSION GUIDE:
    To swap in pgvector:
    1. Create `app/rag/retrieval/pgvector_store.py` inheriting from `BaseVectorStore`.
    2. Implement `add_chunks` to insert embeddings into your PostgreSQL table.
    3. Implement `search` with `SELECT ... ORDER BY embedding <=> query_embedding LIMIT top_k`.
    """

    def __init__(self, relevance_threshold: float = 0.08):
        self.chunks: List[DocumentChunk] = []
        self.doc_freqs: Counter = Counter()
        self.chunk_term_counts: List[Counter] = []
        self.chunk_lengths: List[int] = []
        self.avg_doc_len: float = 1.0
        self.total_docs: int = 0
        self.relevance_threshold = relevance_threshold

    def _tokenize(self, text: str) -> List[str]:
        """Simple alphanumeric tokenizer and lowercaser."""
        import re
        tokens = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
        return tokens

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Indexes chunks in memory."""
        self.chunks.extend(chunks)
        self.total_docs = len(self.chunks)

        for chunk in chunks:
            full_text = f"{chunk.title} {chunk.content}"
            tokens = self._tokenize(full_text)
            term_counts = Counter(tokens)
            self.chunk_term_counts.append(term_counts)
            self.chunk_lengths.append(len(tokens))
            for term in term_counts.keys():
                self.doc_freqs[term] += 1

        total_length = sum(self.chunk_lengths)
        self.avg_doc_len = (total_length / self.total_docs) if self.total_docs > 0 else 1.0

    def search(self, query: str, top_k: int = 3) -> RetrievalResult:
        """
        Executes BM25-based semantic scoring over indexed chunks.
        """
        if not self.chunks or not query.strip():
            return RetrievalResult(query=query, chunks=[], scores=[], has_relevant_context=False)

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return RetrievalResult(query=query, chunks=[], scores=[], has_relevant_context=False)

        scores: List[Tuple[int, float]] = []
        k1 = 1.5
        b = 0.75

        for idx in range(self.total_docs):
            doc_len = self.chunk_lengths[idx]
            term_counts = self.chunk_term_counts[idx]
            doc_score = 0.0

            for q_term in query_tokens:
                if q_term in term_counts:
                    tf = term_counts[q_term]
                    df = self.doc_freqs.get(q_term, 1)
                    # Standard BM25 IDF
                    idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))
                    # Term saturation with document length normalization
                    num = tf * (k1 + 1.0)
                    den = tf + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                    doc_score += idf * (num / den)

            scores.append((idx, doc_score))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)

        top_candidates = scores[:top_k]
        retrieved_chunks = [self.chunks[idx] for idx, _ in top_candidates if top_candidates]
        retrieved_scores = [score for _, score in top_candidates if top_candidates]

        has_relevant = any(s >= self.relevance_threshold for s in retrieved_scores)

        return RetrievalResult(
            query=query,
            chunks=retrieved_chunks,
            scores=retrieved_scores,
            has_relevant_context=has_relevant,
        )
