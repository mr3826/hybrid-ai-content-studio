from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.base import EngineContext
from app.engines.rss.engine import RssEngine
from app.repositories.feed_repository import FeedRepository
from app.repositories.opportunity_repository import OpportunityRepository

router = APIRouter(prefix="/rss", tags=["RSS Discovery"])


class FeedCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    url: str = Field(..., min_length=8, max_length=1024)
    category: str = Field(default="General", max_length=128)
    trust_weight: float = Field(default=0.8, ge=0.1, le=1.0)
    enabled: bool = True


class FeedUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    url: Optional[str] = Field(None, min_length=8, max_length=1024)
    category: Optional[str] = Field(None, max_length=128)
    trust_weight: Optional[float] = Field(None, ge=0.1, le=1.0)
    enabled: Optional[bool] = None


class FeedRead(BaseModel):
    id: str
    name: str
    url: str
    category: str
    trust_weight: float
    enabled: bool
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    failure_count: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateRead(BaseModel):
    id: str
    canonical_url: str
    title: str
    normalized_title: str
    summary: str
    content_fingerprint: str
    primary_source: str
    published_at: datetime
    first_seen_at: datetime
    last_seen_at: datetime
    source_count: int
    sources: List[Dict[str, Any]]
    authority_score: float
    pillar: Optional[str] = None
    niche_score: float
    is_in_niche: bool
    niche_verdict: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/feeds", response_model=List[FeedRead])
async def list_feeds(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    repo = FeedRepository(db)
    return await repo.list_feeds(enabled_only=enabled_only)


@router.post("/feeds", response_model=FeedRead, status_code=status.HTTP_201_CREATED)
async def create_feed(
    payload: FeedCreate,
    db: AsyncSession = Depends(get_db),
):
    repo = FeedRepository(db)
    existing = await repo.get_feed_by_url(payload.url)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Feed with URL '{payload.url}' already exists.",
        )
    feed = await repo.create_feed(payload.model_dump())
    return feed


@router.get("/feeds/{feed_id}", response_model=FeedRead)
async def get_feed(
    feed_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = FeedRepository(db)
    feed = await repo.get_by_id(feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed '{feed_id}' not found.",
        )
    return feed


@router.put("/feeds/{feed_id}", response_model=FeedRead)
async def update_feed(
    feed_id: str,
    payload: FeedUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = FeedRepository(db)
    feed = await repo.get_by_id(feed_id)
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed '{feed_id}' not found.",
        )
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = await repo.update_feed(feed_id, update_data)
    return updated


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = FeedRepository(db)
    success = await repo.delete_feed(feed_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed '{feed_id}' not found.",
        )
    return None


@router.post("/run")
async def run_rss_discovery(
    parameters: Optional[Dict[str, Any]] = None,
):
    """Trigger RSS discovery across all enabled feeds."""
    engine = RssEngine()
    context = EngineContext(
        run_id=f"run_rss_{int(datetime.now().timestamp())}",
        parameters=parameters or {},
    )
    result = await engine.run(context)
    explanation = engine.explain(result)

    return {
        "engine_result": result.model_dump(),
        "explanation": explanation.model_dump(),
    }


@router.post("/dry-run")
async def dry_run_rss_discovery(
    parameters: Optional[Dict[str, Any]] = None,
):
    """Preview RSS discovery results without modifying the database."""
    engine = RssEngine()
    context = EngineContext(
        run_id=f"dry_rss_{int(datetime.now().timestamp())}",
        dry_run=True,
        parameters=parameters or {},
    )
    result = await engine.dry_run(context)
    explanation = engine.explain(result)

    return {
        "engine_result": result.model_dump(),
        "explanation": explanation.model_dump(),
    }


@router.get("/candidates", response_model=List[CandidateRead])
async def list_candidates(
    status: Optional[str] = None,
    pillar: Optional[str] = None,
    in_niche_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    repo = OpportunityRepository(db)
    return await repo.list_opportunities(
        status=status,
        pillar=pillar,
        in_niche_only=in_niche_only,
        limit=limit,
    )


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = OpportunityRepository(db)
    cand = await repo.get_opportunity(candidate_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' not found.",
        )
    return cand
