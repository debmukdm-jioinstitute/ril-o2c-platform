from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.services.market_data import live_status

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "data_source_mode": settings.data_source_mode,
        "live_series_status": live_status(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
