from typing import Any, Dict
from fastapi import APIRouter
from backend.src.core.config import settings

api_router = APIRouter()


@api_router.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }
