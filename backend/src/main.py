from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.api.router import api_router
from backend.src.core.config import settings
from backend.src.core.errors import register_error_handlers
from backend.src.core.logging import setup_logging

# Initialize structured logging
setup_logging()


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    )

    # Register CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Standard Error Handlers (API.md format)
    register_error_handlers(app)

    # Mount Base API Router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
