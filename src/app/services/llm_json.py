"""
Shared helper for parsing a JSON object out of an LLM's raw text reply.
Tolerates surrounding prose and markdown code fences, since not every
provider honors a "JSON only" instruction perfectly.
"""

import json


def extract_json_object(raw_reply: str) -> dict:
    """Extracts the outermost {...} block from a reply.

    Raises ValueError if no JSON object can be found/parsed. Callers should
    catch this and raise their own domain-specific error.
    """
    start = raw_reply.find("{")
    end = raw_reply.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Reply did not contain a JSON object.")
    try:
        return json.loads(raw_reply[start : end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Reply was not valid JSON: {e}") from e
