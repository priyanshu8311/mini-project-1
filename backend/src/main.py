from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.src.api.router import api_router
from backend.src.core.config import settings
from backend.src.core.errors import register_error_handlers
from backend.src.core.logging import setup_logging

# Initialize structured logging
setup_logging()


def create_application() -> FastAPI:
    """FastAPI application factory with security hardening."""
    # Gate API documentation in production environments
    docs_url = None if settings.is_production else f"{settings.API_V1_PREFIX}/docs"
    redoc_url = None if settings.is_production else f"{settings.API_V1_PREFIX}/redoc"
    openapi_url = None if settings.is_production else f"{settings.API_V1_PREFIX}/openapi.json"

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
    )

    # Attach OWASP Security Headers Middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

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
