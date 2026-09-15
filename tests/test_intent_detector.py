"""
Unit tests for Intent Detector and Canned Responses.
Verifies conversational shortcuts (0 tokens) vs domain queries (routing to RAG/LLM).
Operates 100% offline without network calls.
"""

import pytest
from src.app.intent import (
    detect_intent,
    get_canned_response,
    CANNED_RESPONSES,
    INTENT_GREETING,
    INTENT_WELLBEING,
    INTENT_BOT_IDENTITY,
    INTENT_THANKS,
    INTENT_GOODBYE,
    INTENT_ACKNOWLEDGEMENT,
    INTENT_CONFIRMATION,
    INTENT_SIMPLE_NEGATIVE,
    INTENT_SIMPLE_POSITIVE,
    INTENT_CAPABILITY_HELP,
    INTENT_UNKNOWN,
)


@pytest.mark.parametrize(
    "text,expected_intent",
    [
        ("hi", INTENT_GREETING),
        ("hello", INTENT_GREETING),
        ("hey there", INTENT_GREETING),
        ("Good morning!", INTENT_GREETING),
        ("how are you", INTENT_WELLBEING),
        ("How are you doing today?", INTENT_WELLBEING),
        ("who are you?", INTENT_BOT_IDENTITY),
        ("what is your name?", INTENT_BOT_IDENTITY),
        ("thanks", INTENT_THANKS),
        ("Thank you so much!", INTENT_THANKS),
        ("bye", INTENT_GOODBYE),
        ("goodbye!", INTENT_GOODBYE),
        ("ok", INTENT_ACKNOWLEDGEMENT),
        ("got it", INTENT_ACKNOWLEDGEMENT),
        ("yes", INTENT_CONFIRMATION),
        ("sure", INTENT_CONFIRMATION),
        ("no", INTENT_SIMPLE_NEGATIVE),
        ("nope", INTENT_SIMPLE_NEGATIVE),
        ("awesome", INTENT_SIMPLE_POSITIVE),
        ("help", INTENT_CAPABILITY_HELP),
        ("what can you do?", INTENT_CAPABILITY_HELP),
    ],
)
def test_conversational_intents_bypass_llm(text, expected_intent):
    """Verify common conversational messages produce expected non-LLM intent."""
    result = detect_intent(text)
    assert result.intent == expected_intent
    assert result.should_use_llm is False
    assert result.confidence >= 0.9


@pytest.mark.parametrize(
    "query",
    [
        "How do I generate an API key for Apex Cloud?",
        "What are the rate limits for the Growth plan?",
        "Can I configure webhook alerts for latency spikes?",
        "What is serverless compute scaling?",
        "Why am I getting a 401 unauthorized error?",
    ],
)
def test_domain_queries_route_to_llm(query):
    """Verify technical and domain queries route to RAG and LLM."""
    result = detect_intent(query)
    assert result.intent == INTENT_UNKNOWN
    assert result.should_use_llm is True


def test_empty_query_handling():
    """Verify empty or whitespace-only queries default safely to LLM."""
    result = detect_intent("   ")
    assert result.intent == INTENT_UNKNOWN
    assert result.should_use_llm is True


def test_canned_responses_exist():
    """Verify every conversational intent has a corresponding canned response."""
    for intent in [
        INTENT_GREETING,
        INTENT_WELLBEING,
        INTENT_BOT_IDENTITY,
        INTENT_THANKS,
        INTENT_GOODBYE,
        INTENT_CAPABILITY_HELP,
    ]:
        resp = get_canned_response(intent)
        assert resp is not None
        assert len(resp) > 5
        assert intent in CANNED_RESPONSES
