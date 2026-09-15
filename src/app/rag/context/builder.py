"""
Grounded Context Builder & System Prompt Generator.
Constructs system prompts and formats retrieved document chunks into context blocks.
"""

from typing import List
from src.app.schemas.rag import RetrievalResult


class ContextBuilder:
    """Builds formatted context strings and grounded system instructions."""

    @staticmethod
    def build_system_prompt(assistant_name: str = "AI Knowledge Assistant") -> str:
        """
        Generates generic, domain-agnostic grounded RAG system instructions.
        """
        return (
            f"You are {assistant_name}, a knowledgeable and accurate AI documentation guide.\n\n"
            "OPERATING GUIDELINES:\n"
            "1. Answer user questions using the provided [RETRIEVED DOCUMENTATION CONTEXT] below.\n"
            "2. If the retrieved context contains the answer, explain it clearly, concisely, and accurately.\n"
            "3. If the context does NOT contain enough information to answer the question, state honestly that "
            "the documentation does not contain this information. Do NOT invent facts or hallucinate features.\n"
            "4. Do NOT fabricate citations or reference external private data.\n"
            "5. Maintain a professional, helpful, and concise tone."
        )

    @staticmethod
    def format_context_block(retrieval_result: RetrievalResult) -> str:
        """
        Formats retrieved chunks into a markdown-delimited context block for the LLM.
        """
        if not retrieval_result.chunks or not retrieval_result.has_relevant_context:
            return "[RETRIEVED DOCUMENTATION CONTEXT]\nNo relevant documentation found for this query.\n"

        lines: List[str] = ["[RETRIEVED DOCUMENTATION CONTEXT]"]
        for i, chunk in enumerate(retrieval_result.chunks, start=1):
            score_str = f" (relevance: {retrieval_result.scores[i-1]:.2f})" if i - 1 < len(retrieval_result.scores) else ""
            lines.append(f"--- Document #{i}: [{chunk.source}] {chunk.title}{score_str} ---")
            lines.append(chunk.content.strip())
            lines.append("")

        lines.append("[END OF CONTEXT]\n")
        return "\n".join(lines)
