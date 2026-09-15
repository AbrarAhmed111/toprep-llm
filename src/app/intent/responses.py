"""
Generic Canned Responses for Non-LLM Intents.
Kept strictly separate from detection logic.
Returns fast local answers for common conversational interactions (0 LLM cost).

EXTENSION GUIDE:
To add custom domain intents and responses:
1. Define your intent constant in `types.py` (e.g. `INTENT_BUSINESS_HOURS = "business_hours"`).
2. Add regex pattern rules in `detector.py`.
3. If the answer is static, add your canned answer below in `CANNED_RESPONSES`.
   If it requires RAG or dynamic generation, set `should_use_llm = True` in `detector.py`.
"""

from typing import Dict
from .types import (
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
)

CANNED_RESPONSES: Dict[str, str] = {
    INTENT_GREETING: (
        "Hello! I am your AI Knowledge Assistant. How can I assist you with our platform and documentation today?"
    ),
    INTENT_WELLBEING: (
        "I'm doing great, thank you for asking! I'm ready to answer any questions about our products, documentation, or services. How can I help?"
    ),
    INTENT_BOT_IDENTITY: (
        "I am an AI Knowledge and Support Assistant. I help users navigate documentation, answer technical questions, and explain platform features."
    ),
    INTENT_COMPLIMENT: (
        "Thank you! I'm happy to help. Let me know if you have any questions about our platform or documentation."
    ),
    INTENT_PLEASANTRY: (
        "Nice to meet you! Feel free to ask any questions about our platform."
    ),
    INTENT_APOLOGY: (
        "No problem at all! How can I assist you today?"
    ),
    INTENT_PING: (
        "I'm online and ready! What would you like to know?"
    ),
    INTENT_THANKS: (
        "You're very welcome! Let me know if there is anything else I can help you with."
    ),
    INTENT_GOODBYE: (
        "Goodbye! Have a great day, and feel free to return whenever you need assistance."
    ),
    INTENT_ACKNOWLEDGEMENT: (
        "Understood. Let me know what you would like to explore next."
    ),
    INTENT_CONFIRMATION: (
        "Great! Let me know if you have any other questions."
    ),
    INTENT_SIMPLE_NEGATIVE: (
        "No problem. Let me know if anything else comes up."
    ),
    INTENT_SIMPLE_POSITIVE: (
        "Wonderful! How else can I assist you?"
    ),
    INTENT_CANCELLATION: (
        "Operation cancelled. What else can I help you with?"
    ),
    INTENT_SIMPLE_CLARIFICATION: (
        "Could you please specify which topic or feature you would like me to explain?"
    ),
    INTENT_CAPABILITY_HELP: (
        "I can help you with:\n"
        "• Explaining product features and architecture\n"
        "• Searching and answering questions from documentation\n"
        "• API reference, authentication, and integration guides\n"
        "• Pricing plans, limits, and troubleshooting\n\n"
        "What would you like assistance with?"
    ),
}


def get_canned_response(intent: str) -> str:
    """
    Retrieve canned response text for a non-LLM intent.
    Falls back to a polite generic prompt if intent is not recognized.
    """
    return CANNED_RESPONSES.get(
        intent,
        "How can I assist you today?"
    )
