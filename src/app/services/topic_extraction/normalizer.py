"""
Topic Normalization & Deduplication.

Merges naming variants of the same concept extracted from different PDF
chunks (e.g. "React Hooks" / "Hooks in React") into a single canonical
topic, without merging related-but-distinct concepts.

Maps to doc/pdf-extraction.md Stages 16-17. Implemented in Phase 5.
"""
