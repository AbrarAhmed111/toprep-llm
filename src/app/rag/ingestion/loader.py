"""
Document Ingestion Loader.
Discovers and reads Markdown / plain text documents from the knowledge directory.
"""

import os
import logging
from typing import List
from src.app.schemas.rag import DocumentChunk
from src.app.rag.chunking.text_splitter import MarkdownTextSplitter

logger = logging.getLogger("RAGLoader")


class DocumentLoader:
    """Loads and chunks documentation files from a local directory."""

    def __init__(self, directory_path: str, chunk_size: int = 600, chunk_overlap: int = 100):
        self.directory_path = directory_path
        self.splitter = MarkdownTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def load_documents(self) -> List[DocumentChunk]:
        """
        Scans the directory for .md and .txt files, chunks them, and returns all chunks.
        """
        all_chunks: List[DocumentChunk] = []

        if not os.path.exists(self.directory_path):
            logger.warning(f"Knowledge base directory '{self.directory_path}' does not exist.")
            return all_chunks

        for root, _, files in os.walk(self.directory_path):
            for file in files:
                if file.endswith((".md", ".txt")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.directory_path)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        file_chunks = self.splitter.split_document(content, source=rel_path)
                        all_chunks.extend(file_chunks)
                        logger.info(f"Loaded '{rel_path}': {len(file_chunks)} chunks indexed.")
                    except Exception as e:
                        logger.error(f"Failed to read '{file_path}': {e}")

        logger.info(f"📚 Knowledge Base Loaded: {len(all_chunks)} total chunks from '{self.directory_path}'.")
        return all_chunks
