"""
Application Configuration.
Loads validated environment variables with sensible defaults using Pydantic Settings.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings."""

    # Application
    APP_NAME: str = "LLM RAG Starter"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Whitelist (comma-separated strings)
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Assistant Identity
    ASSISTANT_NAME: str = "AI Knowledge Assistant"

    # RAG Knowledge Base Configuration
    KNOWLEDGE_BASE_PATH: str = "knowledge/documents"
    RAG_TOP_K: int = 3
    RAG_CHUNK_SIZE: int = 600
    RAG_CHUNK_OVERLAP: int = 100

    # Gateway Default Settings
    GATEWAY_MAX_ATTEMPTS: int = 10
    GATEWAY_COOLDOWN_SECONDS: int = 60

    # Provider Models & Keys
    # 1. Google Gemini
    GOOGLE_API_KEY1: str = ""
    GOOGLE_API_KEY2: str = ""
    GOOGLE_API_KEY3: str = ""
    GOOGLE_API_KEY4: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_FALLBACK_MODEL: str = "gemini-2.5-flash"

    # 2. Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"

    # 3. OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # 4. Mistral
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-small-latest"

    # 5. Cerebras
    CEREBRAS_API_KEY: str = ""
    CEREBRAS_MODEL: str = "qwen-3.8-27b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_knowledge_path(self) -> str:
        """Resolves knowledge base path whether executed from project root or parent."""
        from pathlib import Path
        p = Path(self.KNOWLEDGE_BASE_PATH)
        if p.is_absolute() and p.exists():
            return str(p)

        # Resolve relative to starter project root (app/../knowledge/documents)
        project_root = Path(__file__).resolve().parent.parent.parent
        candidate = project_root / p
        if candidate.exists():
            return str(candidate)
        return str(p)

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins string into a trimmed list."""
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]



@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for cached configuration settings."""
    return Settings()
