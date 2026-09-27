import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.base import EngineContext, EngineResult
from app.engines.core.registry import engine_registry
from app.engines.opportunity.contracts import (
    OpportunityEngineInput,
    OpportunityScoreBreakdown,
)
from app.engines.opportunity.engine import OpportunityEngine
from app.models.opportunity import Opportunity
from app.repositories.opportunity_repository import OpportunityRepository

router = APIRouter(prefix="/opportunities", tags=["Opportunity Intelligence & Cockpit"])


class OpportunityRead(BaseModel):
    id: str
    topic: str
    slug: str
    candidate_id: Optional[str] = None
    trend_id: Optional[str] = None
    pillar: Optional[str] = None
    status: str
    opportunity_score: float
    trend_score: float
    niche_fit_score: float
    originality_potential: float
    audience_usefulness: float
    evergreen_value: float
    commercial_fit: float
    content_family_potential: float
    sponsor_relevance: float
    saturation_penalty: float
    production_effort: str
    estimated_cost: float
    estimated_time_minutes: int
    suggested_original_angle: str
    suggested_content_family: str
    risks: List[str] = Field(default_factory=list)
    why: str
    recommended_action: str
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    source_references: List[Dict[str, Any]] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RejectRequest(BaseModel):
    rejection_reason: Optional[str] = Field(None, max_length=1000)


class CockpitSummaryResponse(BaseModel):
    signals_today: int
    needs_review: int
    watching: int
    research_ready: int
    in_production: int
    ready_to_publish: int
    published: int
    ai_spend: float
    disk_usage: Dict[str, Any]
    top_opportunities: List[OpportunityRead]
    engine_health_summary: List[Dict[str, Any]]


@router.get("", response_model=List[OpportunityRead])
async def list_opportunities(
    status: Optional[str] = Query(None, description="needs_review, watching, research_ready, rejected, in_production"),
    pillar: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    content_family: Optional[str] = Query(None),
    sort_by: str = Query("opportunity_score", description="opportunity_score, trend_score, originality, recency"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List scored opportunities with filtering and sorting."""
    repo = OpportunityRepository(db)
    return await repo.list_opportunities(
        status=status,
        pillar=pillar,
        min_score=min_score,
        content_family=content_family,
        sort_by=sort_by,
        limit=limit,
    )


@router.get("/cockpit/summary", response_model=CockpitSummaryResponse)
async def get_cockpit_summary(db: AsyncSession = Depends(get_db)):
    """Executive Creator Cockpit dashboard metrics: decisions, lifecycle stages, costs, and top opportunities."""
    repo = OpportunityRepository(db)
    counts = await repo.get_cockpit_counts()
    top_opps = await repo.get_top_opportunities(limit=5)

    # Disk usage stats (SQLite DB size + storage dir)
    db_path = Path("data/db/studio.sqlite")
    db_size = db_path.stat().st_size if db_path.exists() else 0

    media_dir = Path("data/media")
    media_size = sum(f.stat().st_size for f in media_dir.glob("**/*") if f.is_file()) if media_dir.exists() else 0

    # Engine health summary
    health_summary = []
    for eng in engine_registry.list_all():
        try:
            h = eng.health()
            health_summary.append({
                "id": eng.id,
                "name": eng.name,
                "status": h.status,
                "message": h.message,
            })
        except Exception as e:
            health_summary.append({
                "id": eng.id,
                "name": eng.name,
                "status": "failing",
                "message": str(e),
            })

    return CockpitSummaryResponse(
        signals_today=counts["signals_today"],
        needs_review=counts["needs_review"],
        watching=counts["watching"],
        research_ready=counts["research_ready"],
        in_production=counts["in_production"],
        ready_to_publish=counts["ready_to_publish"],
        published=counts["published"],
        ai_spend=0.00,  # Zero AI spend incurred in discovery/trends/opportunity
        disk_usage={
            "database_bytes": db_size,
            "database_mb": round(db_size / (1024 * 1024), 2),
            "media_bytes": media_size,
            "media_mb": round(media_size / (1024 * 1024), 2),
        },
        top_opportunities=[OpportunityRead.model_validate(o) for o in top_opps],
        engine_health_summary=health_summary,
    )


@router.get("/{opportunity_id}", response_model=OpportunityRead)
async def get_opportunity(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    """Get single opportunity with detailed score breakdown and references."""
    repo = OpportunityRepository(db)
    opp = await repo.get_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found.")
    return opp


@router.get("/{opportunity_id}/explain")
async def explain_opportunity(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    """Human-readable explainability for an opportunity's 10 scoring dimensions."""
    repo = OpportunityRepository(db)
    opp = await repo.get_by_id(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found.")

    engine = engine_registry.get("opportunity")
    if engine and isinstance(engine, OpportunityEngine):
        return engine.explain(opp.slug)

    return {
        "result_id": opp.id,
        "summary": opp.why,
        "score_breakdown": opp.score_breakdown,
    }


@router.post("/run", response_model=EngineResult)
async def run_opportunity_engine(
    payload: Optional[OpportunityEngineInput] = None,
    db: AsyncSession = Depends(get_db),
):
    """Run Opportunity Engine across discovered candidates and trend topics."""
    engine = engine_registry.get("opportunity")
    if not engine:
        engine = OpportunityEngine()

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
async def dry_run_opportunity_engine(
    payload: Optional[OpportunityEngineInput] = None,
    db: AsyncSession = Depends(get_db),
):
    """Simulate Opportunity scoring without writing to database."""
    engine = engine_registry.get("opportunity")
    if not engine:
        engine = OpportunityEngine()

    run_id = f"dry_run_{uuid.uuid4()}"
    params = payload.model_dump(mode="json") if payload else {}
    context = EngineContext(
        run_id=run_id,
        dry_run=True,
        trigger="manual",
        parameters=params,
    )
    return await engine.dry_run(context)


# -------------------------------------------------------------
# Human Quality Gate Decisions: [Research], [Watch], [Reject]
# -------------------------------------------------------------

@router.post("/{opportunity_id}/research", response_model=OpportunityRead)
async def approve_for_research(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    """Human Gate: Approve topic for research (transitions status to 'research_ready')."""
    repo = OpportunityRepository(db)
    opp = await repo.update_status(opportunity_id, status="research_ready")
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found.")
    return opp


@router.post("/{opportunity_id}/watch", response_model=OpportunityRead)
async def move_to_watchlist(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    """Human Gate: Put topic on watchlist to observe trend acceleration before producing."""
    repo = OpportunityRepository(db)
    opp = await repo.update_status(opportunity_id, status="watching")
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found.")
    return opp


@router.post("/{opportunity_id}/reject", response_model=OpportunityRead)
async def reject_opportunity(
    opportunity_id: str,
    payload: Optional[RejectRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Human Gate: Reject/dismiss topic with optional editorial reason."""
    repo = OpportunityRepository(db)
    reason = payload.rejection_reason if payload else "Dismissed by creator"
    opp = await repo.update_status(opportunity_id, status="rejected", rejection_reason=reason)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found.")
    return opp
