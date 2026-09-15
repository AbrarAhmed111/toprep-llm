"""
Health Check & Status Endpoints.
Reports operational health, active deployments, and RAG knowledge index status.
"""

from fastapi import APIRouter
from src.app.core.config import get_settings
from src.app.services import gateway, rag_pipeline

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health_check():
    """
    Returns system status, active deployments, and RAG index statistics.
    """
    settings = get_settings()
    available = gateway.get_available_deployments()

    total_chunks = getattr(rag_pipeline.vector_store, "total_docs", 0)

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "rag_index": {
            "indexed_chunks": total_chunks,
            "knowledge_path": settings.KNOWLEDGE_BASE_PATH,
        },
        "gateway": {
            "total_deployments": len(gateway.deployments),
            "available_deployments": len(available),
            "deployments": [
                {
                    "name": d.name,
                    "provider": d.provider,
                    "model": d.default_model,
                    "is_available": d.is_available,
                    "is_disabled": d.is_permanently_disabled,
                }
                for d in gateway.deployments
            ],
        },
    }
