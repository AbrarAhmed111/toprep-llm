"""
Text Normalization Utilities for Intent Detection.
Prepares incoming raw user queries for fast, deterministic pattern matching.
"""

import re
import string
from typing import List, Tuple

# Precompiled regex for stripping punctuation and collapsing whitespace
PUNCTUATION_REGEX = re.compile(f"[{re.escape(string.punctuation)}]")
WHITESPACE_REGEX = re.compile(r"\s+")


def strip_punctuation(text: str) -> str:
    """Removes standard ASCII punctuation and trims excess whitespace."""
    return PUNCTUATION_REGEX.sub(" ", text).strip()


def normalize_text(text: str) -> Tuple[str, str, List[str]]:
    """
    Normalizes input text for multi-tiered intent matching.

    Returns:
        Tuple of (clean_raw_lower, stripped_lower, tokens)
    """
    if not text:
        return "", "", []

    # 1. Lowercased with normalized spaces
    raw_lower = WHITESPACE_REGEX.sub(" ", text.strip().lower())

    # 2. Stripped of punctuation
    stripped = WHITESPACE_REGEX.sub(" ", strip_punctuation(raw_lower))

    # 3. Individual token list
    tokens = stripped.split() if stripped else []

    return raw_lower, stripped, tokens
