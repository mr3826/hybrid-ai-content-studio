from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.base import EngineContext, EngineExplanation, EngineResult
from app.engines.core.registry import engine_registry
from app.engines.trends.contracts import TopicSignal, TrendEngineInput
from app.engines.trends.engine import TrendsEngine
from app.repositories.trend_repository import TrendRepository

router = APIRouter(prefix="/trends", tags=["Trends Engine"])


class TrendHistoryRead(BaseModel):
    id: str
    topic_id: str
    recorded_at: datetime
    trend_score: float
    momentum_score: float
    mention_count: int
    velocity: float
    snapshot_data: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class TrendTopicRead(BaseModel):
    id: str
    topic_key: str
    title: str
    summary: str
    pillar: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    trend_score: float
    momentum_score: float
    mention_count: int
    distinct_sources_count: int
    source_diversity_score: float
    source_authority_score: float
    velocity: float
    velocity_ratio: float
    historical_baseline: float
    first_seen_at: datetime
    last_seen_at: datetime
    manual_boost: float
    is_suppressed: bool
    status: str
    signal_ids: List[str] = Field(default_factory=list)
    source_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrendTopicDetailRead(TrendTopicRead):
    history: List[TrendHistoryRead] = Field(default_factory=list)


class BoostRequest(BaseModel):
    boost_factor: float = Field(..., ge=0.1, le=5.0, description="Multiplier factor e.g. 1.25 or 1.5")


class SuppressRequest(BaseModel):
    suppress: bool = Field(..., description="True to mute/suppress, False to restore")


class ManualSignalCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=512)
    source_name: str = Field(default="Manual Signal", max_length=255)
    summary: str = Field(default="", max_length=4000)
    url: Optional[str] = None
    pillar: Optional[str] = None
    trust_weight: float = Field(default=0.9, ge=0.1, le=1.0)


@router.get("", response_model=List[TrendTopicRead])
async def list_trends(
    status: Optional[str] = Query(None, description="Filter by status: active, emerging, cooling, archived"),
    pillar: Optional[str] = Query(None, description="Filter by niche pillar"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum trend score"),
    is_suppressed: Optional[bool] = Query(None, description="Filter by suppression state"),
    sort_by: str = Query("trend_score", description="Sort by: trend_score, velocity, recency, mentions"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List tracked trend topics with momentum, authority, and velocity metrics."""
    repo = TrendRepository(db)
    return await repo.list_topics(
        status=status,
        pillar=pillar,
        min_score=min_score,
        is_suppressed=is_suppressed,
        sort_by=sort_by,
        limit=limit,
    )


@router.get("/{topic_id}", response_model=TrendTopicDetailRead)
async def get_trend(topic_id: str, db: AsyncSession = Depends(get_db)):
    """Get single trend topic details with full explainability breakdown and history."""
    repo = TrendRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Trend topic {topic_id} not found.")
    return topic


@router.get("/{topic_id}/explain")
async def explain_trend(topic_id: str, db: AsyncSession = Depends(get_db)):
    """Get human-readable explainability breakdown for a trend topic."""
    repo = TrendRepository(db)
    topic = await repo.get_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Trend topic {topic_id} not found.")

    engine = engine_registry.get("trends")
    if engine and isinstance(engine, TrendsEngine):
        return engine.explain(topic.topic_key)

    return {
        "result_id": topic.id,
        "summary": topic.explanation.get("summary", ""),
        "explanation": topic.explanation,
    }


@router.post("/run", response_model=EngineResult)
async def run_trends_engine(
    payload: Optional[TrendEngineInput] = None,
    db: AsyncSession = Depends(get_db),
):
    """Execute Trends Engine to cluster signals, calculate momentum/velocity, and persist topics."""
    engine = engine_registry.get("trends")
    if not engine:
        engine = TrendsEngine()

    run_id = str(uuid.uuid4())
    params = payload.model_dump(mode="json") if payload else {}
    context = EngineContext(
        run_id=run_id,
        dry_run=False,
        trigger="manual",
        parameters=params,
    )
    return await engine.run(context)


@router.post("/dry-run", response_model=EngineResult)
async def dry_run_trends_engine(
    payload: Optional[TrendEngineInput] = None,
    db: AsyncSession = Depends(get_db),
):
    """Simulate Trends Engine analysis without modifying database state."""
    engine = engine_registry.get("trends")
    if not engine:
        engine = TrendsEngine()

    run_id = f"dry_run_{uuid.uuid4()}"
    params = payload.model_dump(mode="json") if payload else {}
    context = EngineContext(
        run_id=run_id,
        dry_run=True,
        trigger="manual",
        parameters=params,
    )
    return await engine.dry_run(context)


@router.post("/{topic_id}/boost", response_model=TrendTopicRead)
async def boost_trend(
    topic_id: str,
    payload: BoostRequest,
    db: AsyncSession = Depends(get_db),
):
    """Apply a manual boost factor (e.g. 1.25x or 1.5x) to a trend topic."""
    repo = TrendRepository(db)
    topic = await repo.apply_boost(topic_id, payload.boost_factor)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Trend topic {topic_id} not found.")
    return topic


@router.post("/{topic_id}/suppress", response_model=TrendTopicRead)
async def suppress_trend(
    topic_id: str,
    payload: SuppressRequest,
    db: AsyncSession = Depends(get_db),
):
    """Toggle manual suppression for an off-target or noisy trend topic."""
    repo = TrendRepository(db)
    topic = await repo.toggle_suppress(topic_id, payload.suppress)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Trend topic {topic_id} not found.")
    return topic


@router.post("/manual-signal", response_model=TrendTopicRead)
async def create_manual_signal(
    payload: ManualSignalCreate,
    db: AsyncSession = Depends(get_db),
):
    """Inject a manual trend signal and immediately incorporate it into topic momentum tracking."""
    sig = TopicSignal(
        signal_id=str(uuid.uuid4()),
        source_type="manual",
        source_name=payload.source_name,
        title=payload.title,
        url=payload.url,
        summary=payload.summary,
        published_at=datetime.now(timezone.utc),
        pillar=payload.pillar,
        trust_weight=payload.trust_weight,
        is_in_niche=True,
    )

    engine = engine_registry.get("trends")
    if not engine:
        engine = TrendsEngine()

    context = EngineContext(
        run_id=str(uuid.uuid4()),
        dry_run=False,
        trigger="manual_signal",
        parameters={"custom_signals": [sig.model_dump(mode="json")]},
    )
    result = await engine.run(context)

    # Return the newly created/updated topic
    repo = TrendRepository(db)
    if result.outputs:
        topic_key = result.outputs[0].get("topic_key")
        if topic_key:
            topic = await repo.get_by_key(topic_key)
            if topic:
                return topic

    topics = await repo.list_topics(limit=1, sort_by="recency")
    if topics:
        return topics[0]

    raise HTTPException(status_code=500, detail="Failed to create trend topic from signal.")
