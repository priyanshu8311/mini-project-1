from typing import Any

from fastapi import APIRouter

from backend.src.api.auth import auth_router
from backend.src.api.forecasting import forecasting_router
from backend.src.api.integrations import integrations_router
from backend.src.api.inventory import inventory_router
from backend.src.api.locations import locations_router
from backend.src.api.products import products_router
from backend.src.api.purchasing import purchasing_router
from backend.src.api.users import users_router
from backend.src.api.webhooks import webhooks_router
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
api_router.include_router(inventory_router)
api_router.include_router(purchasing_router)
api_router.include_router(forecasting_router)
api_router.include_router(integrations_router)
api_router.include_router(webhooks_router)
