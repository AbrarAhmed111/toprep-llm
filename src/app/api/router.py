"""
Central API Router.
Aggregates and prefixes domain route handlers under /api.
"""

from fastapi import APIRouter
from src.app.api.routes.health import router as health_router
from src.app.api.routes.chat import router as chat_router
from src.app.api.routes.topics import router as topics_router
from src.app.api.routes.ai import router as ai_router

api_router = APIRouter(prefix="/api")

# Mount sub-routers
api_router.include_router(chat_router)
api_router.include_router(topics_router)
api_router.include_router(ai_router)
api_router.include_router(health_router)
