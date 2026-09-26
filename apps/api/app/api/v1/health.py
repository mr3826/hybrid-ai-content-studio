from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import check_db_health
from app.engines.core.registry import engine_registry

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
    app_env: str
    registered_engines: int
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def get_health(response: Response) -> HealthResponse:
    db_connected = await check_db_health()
    if not db_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        db_status = "disconnected"
        overall_status = "degraded"
    else:
        db_status = "connected"
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        version="0.1.0",
        app_env=settings.APP_ENV,
        registered_engines=len(engine_registry.list_all()),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
