"""
LLM Topic Extraction.

Runs each PDF chunk through the LLM gateway (see
services.chat_service.gateway) to extract candidate learning topics,
following the same system/human message + tolerant JSON parsing +
typed-error pattern as topic_organizer_service.py.

Maps to doc/pdf-extraction.md Stages 10, 13-15. Implemented in Phase 5.
"""
