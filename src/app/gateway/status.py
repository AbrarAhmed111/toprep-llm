"""
Provider Status Event Definitions.
Represents user-facing status updates when fallback or provider switching occurs.
"""

from dataclasses import dataclass


@dataclass
class ProviderStatusEvent:
    """Status event indicating a provider fallback, switch, or outage."""
    type: str  # "provider_status"
    status: str  # "fallback" or "switched"
    message: str  # User-facing message
    provider: str  # Name of deployment
