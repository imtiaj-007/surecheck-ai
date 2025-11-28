"""API v1 router aggregation."""

from fastapi import APIRouter

from .claim import router as claims_router

api_router = APIRouter()


# Include endpoints
api_router.include_router(claims_router, prefix="/claim", tags=["Claim"])

__all__ = ["api_router"]
