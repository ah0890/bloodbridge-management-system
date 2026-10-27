import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings

logger = logging.getLogger("bloodbridge")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="BloodBridge API",
        version="0.1.0",
        description=(
            "Blood bank management API. Demo deployments contain SYNTHETIC DEMO DATA only; "
            "no endpoint reflects live real-world blood inventory or real donors."
        ),
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):  # pragma: no cover - defensive
        # Never echo internals (which could include record contents) back to clients.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
