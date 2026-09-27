import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.base import EngineContext, EngineResult
from app.engines.core.registry import engine_registry
from app.engines.research.contracts import (
    ResearchEngineInput,
    ResearchPacketCreateRequest,
    ResearchPacketUpdateRequest,
)
from app.engines.research.engine import ResearchEngine
from app.models.research import ResearchPacket, ResearchRevision
from app.repositories.research_repository import ResearchRepository

router = APIRouter(prefix="/research", tags=["Evidence-Based Research Engine"])


class ResearchRevisionRead(BaseModel):
    id: str
    packet_id: str
    revision_number: int
    changed_by: str
    change_summary: str
    snapshot: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResearchPacketRead(BaseModel):
    id: str
    opportunity_id: Optional[str] = None
    topic: str
    slug: str
    summary: str
    primary_sources: List[Dict[str, Any]] = Field(default_factory=list)
    supporting_sources: List[Dict[str, Any]] = Field(default_factory=list)
    facts: List[Dict[str, Any]] = Field(default_factory=list)
    numbers: List[Dict[str, Any]] = Field(default_factory=list)
    dates: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    uncertain_claims: List[Dict[str, Any]] = Field(default_factory=list)
    things_not_to_claim: List[Dict[str, Any]] = Field(default_factory=list)
    version: int
    is_verified: bool
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    revisions: List[ResearchRevisionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/packets", response_model=ResearchPacketRead, status_code=status.HTTP_201_CREATED)
async def create_or_generate_packet(
    req: ResearchPacketCreateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Generate or retrieve a traceable research packet for an opportunity or topic."""
    engine = engine_registry.get("research")
    if not engine or not isinstance(engine, ResearchEngine):
        engine = ResearchEngine()

    repo = ResearchRepository(session)

    # Check if a packet already exists for this opportunity
    if req.opportunity_id:
        existing = await repo.get_by_opportunity_id(req.opportunity_id)
        if existing:
            return existing

    engine_input = ResearchEngineInput(
        opportunity_id=req.opportunity_id,
        topic=req.topic,
        raw_sources=req.sources,
        raw_text=req.raw_text,
        context=req.context,
        dry_run=False,
    )

    packet_item = await engine.generate_packet(engine_input, session, dry_run=False)
    created_packet = await repo.get_by_id(packet_item.id)
    if not created_packet:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generated research packet",
        )
    return created_packet


@router.get("/packets", response_model=List[ResearchPacketRead])
async def list_packets(
    opportunity_id: Optional[str] = None,
    is_verified: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """List research packets with optional filters."""
    repo = ResearchRepository(session)
    return await repo.list_packets(
        opportunity_id=opportunity_id,
        is_verified=is_verified,
        search=search,
        limit=limit,
    )


@router.get("/packets/{packet_id}", response_model=ResearchPacketRead)
async def get_packet(
    packet_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Retrieve detailed research packet with full citation breakdown and revisions."""
    repo = ResearchRepository(session)
    packet = await repo.get_by_id(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail=f"Research packet '{packet_id}' not found.")
    return packet


@router.put("/packets/{packet_id}", response_model=ResearchPacketRead)
async def update_packet(
    packet_id: str,
    req: ResearchPacketUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Update research packet contents with creator corrections and archive prior revision."""
    repo = ResearchRepository(session)
    packet = await repo.get_by_id(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail=f"Research packet '{packet_id}' not found.")

    updates = req.model_dump(exclude_unset=True)
    changed_by = updates.pop("changed_by", "creator")
    change_summary = updates.pop("change_summary", "Manual edit by creator")

    updated_packet = await repo.update_packet(
        packet=packet,
        updates=updates,
        changed_by=changed_by,
        change_summary=change_summary,
    )
    await session.commit()
    return await repo.get_by_id(packet_id)


@router.post("/packets/{packet_id}/verify", response_model=ResearchPacketRead)
async def verify_packet(
    packet_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Human Quality Gate: Explicitly verify research packet facts and citations."""
    repo = ResearchRepository(session)
    packet = await repo.verify_packet(packet_id=packet_id, verified_by="creator")
    if not packet:
        raise HTTPException(status_code=404, detail=f"Research packet '{packet_id}' not found.")
    await session.commit()
    return packet


@router.get("/packets/{packet_id}/revisions", response_model=List[ResearchRevisionRead])
async def get_packet_revisions(
    packet_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Fetch revision history and audit snapshots for a packet."""
    repo = ResearchRepository(session)
    return await repo.get_revisions(packet_id)


@router.post("/packets/{packet_id}/revert/{revision_number}", response_model=ResearchPacketRead)
async def revert_packet_revision(
    packet_id: str,
    revision_number: int,
    session: AsyncSession = Depends(get_db),
):
    """Revert research packet to an earlier revision snapshot."""
    repo = ResearchRepository(session)
    packet = await repo.revert_to_revision(packet_id=packet_id, revision_number=revision_number)
    if not packet:
        raise HTTPException(
            status_code=404,
            detail=f"Packet '{packet_id}' or revision #{revision_number} not found.",
        )
    await session.commit()
    return packet


@router.post("/run", response_model=EngineResult)
async def run_research_engine(
    payload: Optional[Dict[str, Any]] = None,
):
    """Direct execution trigger for the Research Engine."""
    engine = engine_registry.get("research")
    if not engine:
        raise HTTPException(status_code=500, detail="Research Engine not found in registry.")

    context = EngineContext(
        run_id=str(uuid.uuid4()),
        project_id="default",
        dry_run=False,
        trigger="manual",
    )
    return await engine.run(context, payload or {})
