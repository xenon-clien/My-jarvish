"""Health check endpoint for JARVIS AI."""
from fastapi import APIRouter
from backend.core.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Return system health and operational readiness."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "ai_provider": settings.AI_PROVIDER,
        "wake_word": settings.WAKE_WORD,
    }
