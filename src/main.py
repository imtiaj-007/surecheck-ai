from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import api_router
from src.core.config import settings
from src.core.redis import close_redis, init_redis
from src.utils.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown events.
    Initialize DB connections, check S3, or warm up LLMs.
    """
    log.info(f"🚀 Starting SureCheck AI in {settings.APP_ENV} mode...")
    log.info(f"✅ Loaded Settings for: {settings.APP_ENV}")
    await init_redis()

    yield

    log.info("🛑 Shutting down SureCheck AI...")
    await close_redis()


app: FastAPI = FastAPI(
    title="SureCheck AI",
    summary="Intelligent Medical Claims Processing Platform",
    description=(
        "**SureCheck AI** is an advanced, AI-powered backend system transforming the medical insurance claims process. "
        "It streamlines the adjudication workflow: document ingestion and classification, structured data extraction, "
        "cross-validation, and automated decision-making, resulting in faster and more accurate claims processing."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Middleware configuration
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True)

# Include API Router
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get(
    "/",
    name="root",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, Any],
    summary="Root Endpoint",
    description="Health check endpoint. Returns the status of the SureCheck API service, confirming the server is operational.",
    tags=["Health"],
)
async def root_route() -> dict[str, Any]:
    """
    Health check endpoint for SureCheck AI API.
    """
    return {
        "status": "ok",
        "message": "SureCheck AI is live and running 💉",
        "environment": settings.APP_ENV,
        "version": app.version,
    }
