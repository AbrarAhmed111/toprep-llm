"""
Intent Types & Data Structures.
Defines intent classification results, pattern rules, and standard generic intent constants.
"""

from dataclasses import dataclass, field
from typing import List, Pattern

# -----------------------------------------------------------------------------
# Standard Conversational Non-LLM Intents (0 LLM tokens, instant response)
# -----------------------------------------------------------------------------
INTENT_GREETING = "greeting"
INTENT_WELLBEING = "wellbeing"
INTENT_BOT_IDENTITY = "bot_identity"
INTENT_COMPLIMENT = "compliment"
INTENT_PLEASANTRY = "pleasantry"
INTENT_APOLOGY = "apology"
INTENT_PING = "ping"
INTENT_THANKS = "thanks"
INTENT_GOODBYE = "goodbye"
INTENT_ACKNOWLEDGEMENT = "acknowledgement"
INTENT_CONFIRMATION = "confirmation"
INTENT_SIMPLE_NEGATIVE = "simple_negative"
INTENT_SIMPLE_POSITIVE = "simple_positive"
INTENT_CANCELLATION = "cancellation"
INTENT_SIMPLE_CLARIFICATION = "simple_clarification"
INTENT_CAPABILITY_HELP = "capability_help"

# Default fallback for knowledge / product questions -> Routes to RAG & LLM
INTENT_UNKNOWN = "unknown"

# Set of intents that are answered locally via canned responses (0 LLM cost)
NON_LLM_INTENTS = {
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
}


@dataclass
class IntentResult:
    """Outcome of evaluating a user message against intent detection rules."""
    intent: str
    confidence: float
    should_use_llm: bool
    matched_rule: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class IntentRule:
    """A pattern matching rule evaluated against normalized text."""
    intent: str
    patterns: List[Pattern]
    confidence: float = 1.0
    should_use_llm: bool = False
    priority: int = 0
