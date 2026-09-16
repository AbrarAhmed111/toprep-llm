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
    APP_NAME: str = "LLM Gateway Service"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Whitelist (comma-separated strings)
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

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

    # PDF Ingestion (see doc/pdf-extraction-phases.md)
    PDF_MAX_SIZE_BYTES: int = 15 * 1024 * 1024  # 15MB, matches the frontend's upload cap
    PDF_MIN_TEXT_CHARS_PER_PAGE: int = 20  # below this, a page falls back to OCR
    PDF_OCR_ENABLED: bool = True  # disable in environments without a Tesseract install
    PDF_CHUNK_MAX_CHARS: int = 8000  # per-chunk character budget when no TOC-based boundaries exist
    PDF_PIPELINE_TIMEOUT_SECONDS: float = 120.0  # caps the whole extract-pdf request (multi-chunk LLM calls)

    # YouTube Data API Configuration
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_API_BASE_URL: str = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_REQUEST_TIMEOUT: float = 15.0
    YOUTUBE_DEFAULT_MAX_RESULTS: int = 10
    YOUTUBE_MAX_RESULTS_LIMIT: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
