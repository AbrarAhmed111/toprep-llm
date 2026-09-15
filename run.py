"""
Server entrypoint for LLM RAG Starter.
Runs FastAPI with Uvicorn in development mode with hot-reloading.
"""

import uvicorn
from src.app.core.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "src.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
