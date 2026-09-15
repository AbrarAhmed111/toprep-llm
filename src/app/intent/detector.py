"""
Deterministic Intent Detector.
Evaluates user messages against fast compiled regex patterns.
Operates 100% offline without LLM calls or cloud APIs.
"""

import re
from typing import List, Tuple

from .normalizer import normalize_text, strip_punctuation
from .types import (
    IntentResult,
    IntentRule,
    INTENT_GREETING,
    INTENT_WELLBEING,
    INTENT_BOT_IDENTITY,
    INTENT_COMPLIMENT,
    INTENT_PLEASANTRY,
    INTENT_APOLOGY,
    INTENT_PING,
    INTENT_THANKS,
    INTENT_GOODBYE,
    INTENT_ACKNOWLEDGEMENT,
    INTENT_CONFIRMATION,
    INTENT_SIMPLE_NEGATIVE,
    INTENT_SIMPLE_POSITIVE,
    INTENT_CANCELLATION,
    INTENT_SIMPLE_CLARIFICATION,
    INTENT_CAPABILITY_HELP,
    INTENT_UNKNOWN,
)

# -----------------------------------------------------------------------------
# Precompiled Regex Pattern Definitions
# -----------------------------------------------------------------------------
GREETING_PATTERNS = [
    re.compile(r"^(hi|hello|hey|hiya|howdy|holla)( there| all| bot)?$", re.IGNORECASE),
    re.compile(r"^(good morning|good afternoon|good evening|good day)( there)?$", re.IGNORECASE),
    re.compile(r"^(greetings|salutations)$", re.IGNORECASE),
    re.compile(r"^(salam|assalam\s*o\s*alaikum|as-salamu\s*alaykum)$", re.IGNORECASE),
]

WELLBEING_PATTERNS = [
    re.compile(r"^(how are you|how r u|how are you doing|how do you do|how is it going|hows it going)(\s+(today|doing|bot))?$", re.IGNORECASE),
    re.compile(r"^(are you okay|are you well|hope you are doing well)$", re.IGNORECASE),
    re.compile(r"^(what('?s| is) up|wassup|sup)$", re.IGNORECASE),
]

BOT_IDENTITY_PATTERNS = [
    re.compile(r"^(who are you|what is your name|whats your name|what are you|tell me about yourself|are you a bot|are you human|are you an ai)(\??)$", re.IGNORECASE),
]

COMPLIMENT_PATTERNS = [
    re.compile(r"^(you are (great|awesome|amazing|helpful|smart|the best)|good job|well done|nice job)$", re.IGNORECASE),
    re.compile(r"^(great job|love you|cool bot|smart bot)$", re.IGNORECASE),
]

PLEASANTRY_PATTERNS = [
    re.compile(r"^(nice to meet you|pleased to meet you|glad to meet you)$", re.IGNORECASE),
]

APOLOGY_PATTERNS = [
    re.compile(r"^(sorry|i am sorry|my bad|apologies|excuse me)$", re.IGNORECASE),
]

PING_PATTERNS = [
    re.compile(r"^(test|testing|ping|hello\?|are you there\?|is anyone there\?)$", re.IGNORECASE),
]

THANKS_PATTERNS = [
    re.compile(r"^(thanks|thank you|thx|ty|many thanks|thank you so much|thanks a lot|much appreciated)$", re.IGNORECASE),
    re.compile(r"^(thank you for (your )?help)$", re.IGNORECASE),
]

GOODBYE_PATTERNS = [
    re.compile(r"^(bye|goodbye|see you|cya|take care|have a good day|bye bye|farewell)$", re.IGNORECASE),
]

ACKNOWLEDGEMENT_PATTERNS = [
    re.compile(r"^(ok|okay|k|kk|got it|understood|i see|alright|cool|noted)$", re.IGNORECASE),
]

CONFIRMATION_PATTERNS = [
    re.compile(r"^(yes|yeah|yep|yup|aye|sure|definitely|absolutely|certainly|correct|indeed)$", re.IGNORECASE),
]

SIMPLE_NEGATIVE_PATTERNS = [
    re.compile(r"^(no|nope|nah|not really|negative|no thanks|no thank you)$", re.IGNORECASE),
]

SIMPLE_POSITIVE_PATTERNS = [
    re.compile(r"^(great|awesome|perfect|excellent|wonderful|super)$", re.IGNORECASE),
]

CANCELLATION_PATTERNS = [
    re.compile(r"^(cancel|abort|stop|quit|exit|nevermind|never mind)$", re.IGNORECASE),
]

SIMPLE_CLARIFICATION_PATTERNS = [
    re.compile(r"^(what|why|how|pardon|what do you mean|huh)\??$", re.IGNORECASE),
]

CAPABILITY_HELP_PATTERNS = [
    re.compile(r"^(help|help me|what can you do|how can you help|what are your capabilities|features|commands|options|what do you do)\??$", re.IGNORECASE),
]


CONVERSATIONAL_RULES: List[Tuple[str, List[re.Pattern]]] = [
    (INTENT_GREETING, GREETING_PATTERNS),
    (INTENT_WELLBEING, WELLBEING_PATTERNS),
    (INTENT_BOT_IDENTITY, BOT_IDENTITY_PATTERNS),
    (INTENT_CAPABILITY_HELP, CAPABILITY_HELP_PATTERNS),
    (INTENT_COMPLIMENT, COMPLIMENT_PATTERNS),
    (INTENT_PLEASANTRY, PLEASANTRY_PATTERNS),
    (INTENT_APOLOGY, APOLOGY_PATTERNS),
    (INTENT_PING, PING_PATTERNS),
    (INTENT_THANKS, THANKS_PATTERNS),
    (INTENT_GOODBYE, GOODBYE_PATTERNS),
    (INTENT_ACKNOWLEDGEMENT, ACKNOWLEDGEMENT_PATTERNS),
    (INTENT_CONFIRMATION, CONFIRMATION_PATTERNS),
    (INTENT_SIMPLE_NEGATIVE, SIMPLE_NEGATIVE_PATTERNS),
    (INTENT_SIMPLE_POSITIVE, SIMPLE_POSITIVE_PATTERNS),
    (INTENT_CANCELLATION, CANCELLATION_PATTERNS),
    (INTENT_SIMPLE_CLARIFICATION, SIMPLE_CLARIFICATION_PATTERNS),
]


def detect_intent(text: str) -> IntentResult:
    """
    Classify incoming text into an IntentResult.

    1. Checks conversational non-LLM patterns (short greetings, thanks, wellbeing).
       Returns should_use_llm = False (0 tokens consumed).
    2. If not matched, returns INTENT_UNKNOWN with should_use_llm = True,
       routing query to the RAG knowledge retriever and LLM Gateway.
    """
    if not text or not text.strip():
        return IntentResult(
            intent=INTENT_UNKNOWN,
            confidence=0.0,
            should_use_llm=True,
            matched_rule="empty_text",
        )

    raw_lower, stripped, tokens = normalize_text(text)

    # 1. Evaluate conversational rules
    for intent, patterns in CONVERSATIONAL_RULES:
        for pat in patterns:
            if pat.match(stripped) or pat.match(raw_lower):
                return IntentResult(
                    intent=intent,
                    confidence=1.0,
                    should_use_llm=False,
                    matched_rule=f"regex:{pat.pattern}",
                )

    # 2. Default: Substantive domain query -> RAG + LLM Gateway
    return IntentResult(
        intent=INTENT_UNKNOWN,
        confidence=0.0,
        should_use_llm=True,
        matched_rule="fallback_to_llm",
    )
