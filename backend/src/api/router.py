from typing import Any

from fastapi import APIRouter

from backend.src.api.auth import auth_router
from backend.src.api.locations import locations_router
from backend.src.api.products import products_router
from backend.src.api.users import users_router
from backend.src.core.config import settings

api_router = APIRouter()


# Health check
@api_router.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


# Include Domain Routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(products_router)
api_router.include_router(locations_router)
