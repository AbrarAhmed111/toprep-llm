"""
Provider Deployment Representation.
Tracks credentials, base URL, model name, and temporary cooldown / permanent disablement state.
"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderDeployment:
    """Represents a specific LLM provider deployment instance."""
    name: str              # User-friendly name, e.g. "Gemini #1", "Groq Primary"
    provider: str          # Provider family: "gemini", "groq", "openai", "mistral", "cerebras"
    api_key: str           # Secret API key (never exposed in output or logs)
    base_url: Optional[str]# Custom API base URL if OpenAI-compatible
    default_model: str     # Provider-specific model name
    cooldown_seconds: int = 60
    cooldown_until: float = 0.0
    is_permanently_disabled: bool = False

    @property
    def is_available(self) -> bool:
        """Returns True if the deployment is not disabled and not currently in cooldown."""
        if self.is_permanently_disabled:
            return False
        return time.time() >= self.cooldown_until

    def mark_cooldown(self, seconds: Optional[int] = None) -> None:
        """Put this deployment on temporary cooldown after a rate limit or transient failure."""
        duration = seconds or self.cooldown_seconds
        self.cooldown_until = time.time() + duration

    def mark_disabled(self) -> None:
        """Mark deployment as permanently disabled (e.g. invalid API key or decommissioned model)."""
        self.is_permanently_disabled = True
