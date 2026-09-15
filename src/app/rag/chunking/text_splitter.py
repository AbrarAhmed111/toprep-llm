"""
Recursive Markdown & Text Splitter.
Splits documents into coherent chunks while preserving markdown headings and section titles.
"""

import re
from typing import List
from src.app.schemas.rag import DocumentChunk


class MarkdownTextSplitter:
    """
    Recursively splits markdown text by headings, paragraphs, and sentence boundaries.
    """

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document(self, text: str, source: str) -> List[DocumentChunk]:
        """
        Splits markdown text into DocumentChunk objects with source and heading metadata.
        """
        if not text or not text.strip():
            return []

        # Find sections by markdown headings (e.g. ## Title)
        sections = self._split_by_headings(text)
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        for section_title, section_content in sections:
            section_chunks = self._chunk_text(section_content)
            for content in section_chunks:
                if not content.strip():
                    continue
                chunk_id = f"{source}#chunk-{chunk_idx}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        source=source,
                        title=section_title,
                        content=content.strip(),
                        metadata={"chunk_index": chunk_idx},
                    )
                )
                chunk_idx += 1

        return chunks

    def _split_by_headings(self, text: str) -> List[tuple[str, str]]:
        """Splits markdown into (heading, text) pairs based on headers."""
        lines = text.splitlines()
        sections: List[tuple[str, str]] = []
        current_heading = "General"
        current_lines: List[str] = []

        heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            match = heading_pattern.match(line.strip())
            if match:
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines)))
                    current_lines = []
                current_heading = match.group(2).strip()
            current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines)))

        return sections

    def _chunk_text(self, text: str) -> List[str]:
        """Splits text into chunks of roughly chunk_size with chunk_overlap."""
        paragraphs = text.split("\n\n")
        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If paragraph itself is larger than chunk_size, split by sentences/lines
                if len(para) > self.chunk_size:
                    sub_parts = self._split_long_paragraph(para)
                    chunks.extend(sub_parts[:-1])
                    current_chunk = sub_parts[-1] if sub_parts else ""
                else:
                    # Apply overlap from end of previous chunk if possible
                    overlap_prefix = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                    current_chunk = f"{overlap_prefix}\n\n{para}".strip() if overlap_prefix else para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_long_paragraph(self, para: str) -> List[str]:
        """Splits very long paragraphs on sentence boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", para)
        parts: List[str] = []
        curr = ""
        for s in sentences:
            if len(curr) + len(s) + 1 <= self.chunk_size:
                curr = f"{curr} {s}".strip()
            else:
                if curr:
                    parts.append(curr)
                curr = s
        if curr:
            parts.append(curr)
        return parts or [para]
