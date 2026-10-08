import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
    AIResponse,
    AIProviderStatus,
    ProviderName,
)
from app.engines.ai.engine import AIProviderEngine
from app.engines.core.base import EngineContext, EngineResult
from app.engines.core.registry import engine_registry
from app.repositories.ai_repository import AIRepository

router = APIRouter(prefix="/ai", tags=["AI Provider Engine"])


def get_ai_engine() -> AIProviderEngine:
    engine = engine_registry.get("ai")
    if not engine or not isinstance(engine, AIProviderEngine):
        engine = AIProviderEngine()
    return engine


class AIInvocationLogRead(BaseModel):
    id: str
    provider: str
    model: str
    task: str
    prompt_version: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    latency_ms: float
    success: bool
    error_message: Optional[str] = None
    fallback_used: bool
    fallback_reason: Optional[str] = None
    primary_provider: Optional[str] = None
    primary_error: Optional[str] = None
    prompt_hash: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunRequest(BaseModel):
    dry_run: bool = False
    task: str = "generate_text"
    prompt: str = "Benchmark prompt"
    preferred_provider: Optional[ProviderName] = None
    simulate_failure: Optional[str] = None


@router.get("/status", response_model=AIProviderStatus)
async def get_status(
    db: AsyncSession = Depends(get_db),
    engine: AIProviderEngine = Depends(get_ai_engine),
):
    """Get active provider adapters, models, health, and budget status."""
    return await engine.get_status(session=db)


@router.post("/generate-text", response_model=AIResponse)
async def generate_text(
    request: TextGenerationRequest,
    db: AsyncSession = Depends(get_db),
    engine: AIProviderEngine = Depends(get_ai_engine),
):
    """Centralized unstructured text generation with primary adapter and technical fallback."""
    return await engine.generate_text(request, session=db)


@router.post("/generate-structured", response_model=AIResponse)
async def generate_structured(
    request: StructuredGenerationRequest,
    db: AsyncSession = Depends(get_db),
    engine: AIProviderEngine = Depends(get_ai_engine),
):
    """Centralized schema-enforced JSON generation with primary adapter and schema fallback."""
    return await engine.generate_structured(request, session=db)


@router.post("/analyze", response_model=AIResponse)
async def analyze_content(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    engine: AIProviderEngine = Depends(get_ai_engine),
):
    """Centralized content and claim auditing with technical fallback."""
    return await engine.analyze(request, session=db)


@router.get("/logs", response_model=List[AIInvocationLogRead])
async def list_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: Optional[str] = Query(None),
    task: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    fallback_used: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List historical AI invocation telemetry logs."""
    repo = AIRepository(db)
    return await repo.list_logs(
        limit=limit,
        offset=offset,
        provider=provider,
        task=task,
        success=success,
        fallback_used=fallback_used,
    )


@router.get("/analytics")
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated token usage, cost, latency, and fallback metrics."""
    repo = AIRepository(db)
    return await repo.get_analytics_summary(days=days)


@router.post("/run", response_model=EngineResult)
async def run_ai_engine(
    body: RunRequest,
    engine: AIProviderEngine = Depends(get_ai_engine),
):
    """Execute AI provider engine run adhering to BaseEngine contract."""
    context = EngineContext(
        run_id=str(uuid.uuid4()),
        dry_run=body.dry_run,
        trigger="manual_api",
        parameters=body.model_dump(),
    )
    return await engine.run(context)


@router.post("/dry-run", response_model=EngineResult)
async def dry_run_ai_engine(
    body: RunRequest,
    engine: AIProviderEngine = Depends(get_ai_engine),
):
    """Simulate AI provider execution without committing changes."""
    context = EngineContext(
        run_id=str(uuid.uuid4()),
        dry_run=True,
        trigger="manual_dry_run",
        parameters=body.model_dump(),
    )
    return await engine.dry_run(context)
