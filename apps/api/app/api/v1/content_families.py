from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.registry import engine_registry
from app.engines.content_family.contracts import (
    ContentFamilyCreateInput,
    ContentFamilyUpdateInput,
    ContentItemCreateInput,
    ContentItemUpdateInput,
)
from app.engines.content_family.engine import ContentFamilyEngine
from app.repositories.content_family_repository import (
    ContentFamilyRepository,
    ContentItemRepository,
)
from app.repositories.evidence_repository import EvidenceRepository

router = APIRouter(tags=["content_families"])


class LinkEvidenceClaimRequest(BaseModel):
    claim_id: str = Field(..., description="ID of the claim to link to this child item")
    relevance_note: Optional[str] = Field(None, description="Optional note explaining how child uses this claim")
    is_primary: bool = Field(False, description="Whether this is the child's primary focal claim")


class ApproveFamilyRequest(BaseModel):
    reviewer: Optional[str] = Field("creator", description="Reviewer identifier")


# ---------------------------------------------------------------------------
# Content Family Endpoints
# ---------------------------------------------------------------------------

@router.get("/content-families/health")
async def content_family_health():
    """Health check for Content Family Engine."""
    engine = engine_registry.get("content_family")
    if engine:
        return engine.health()
    return {"status": "unregistered", "engine_id": "content_family"}


@router.post("/content-families", status_code=status.HTTP_201_CREATED)
async def create_content_family(
    payload: ContentFamilyCreateInput,
    db: AsyncSession = Depends(get_db),
):
    """Create a new Content Family representing an empirical research/originality investment."""
    repo = ContentFamilyRepository(db)
    family = await repo.create_family(
        title=payload.title,
        content_pillar=payload.content_pillar,
        original_value_type=payload.original_value_type,
        summary=payload.summary,
        topic_id=payload.topic_id,
        research_packet_id=payload.research_packet_id,
        originality_plan_id=payload.originality_plan_id,
        primary_experiment_id=payload.primary_experiment_id,
        research_cost=payload.research_cost,
        experiment_cost=payload.experiment_cost,
        ai_cost=payload.ai_cost,
        media_cost=payload.media_cost,
        manual_time_minutes=payload.manual_time_minutes,
        local_compute_seconds=payload.local_compute_seconds,
    )
    return {
        "id": family.id,
        "title": family.title,
        "slug": family.slug,
        "status": family.status,
        "content_pillar": family.content_pillar,
        "original_value_type": family.original_value_type,
        "summary": family.summary,
        "topic_id": family.topic_id,
        "research_packet_id": family.research_packet_id,
        "originality_plan_id": family.originality_plan_id,
        "primary_experiment_id": family.primary_experiment_id,
        "created_at": family.created_at.isoformat() if family.created_at else None,
    }


@router.get("/content-families")
async def list_content_families(
    status_filter: Optional[str] = Query(None, alias="status"),
    content_pillar: Optional[str] = Query(None),
    topic_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List Content Families with optional status and pillar filters."""
    repo = ContentFamilyRepository(db)
    families = await repo.list_families(
        status=status_filter,
        content_pillar=content_pillar,
        topic_id=topic_id,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": f.id,
            "title": f.title,
            "slug": f.slug,
            "status": f.status,
            "content_pillar": f.content_pillar,
            "original_value_type": f.original_value_type,
            "summary": f.summary,
            "topic_id": f.topic_id,
            "research_packet_id": f.research_packet_id,
            "originality_plan_id": f.originality_plan_id,
            "primary_experiment_id": f.primary_experiment_id,
            "item_count": len(f.items) if f.items else 0,
            "shared_cost": round(f.research_cost + f.experiment_cost + f.ai_cost + f.media_cost, 4),
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "approved_at": f.approved_at.isoformat() if f.approved_at else None,
        }
        for f in families
    ]


@router.get("/content-families/{family_id}")
async def get_content_family(
    family_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a Content Family including child items and economics."""
    repo = ContentFamilyRepository(db)
    family = await repo.get_family(family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentFamily {family_id} not found",
        )

    economics = await repo.calculate_economics(family_id)

    items_data = []
    for item in family.items:
        evidence_data = [
            {
                "id": sel.id,
                "claim_id": sel.claim_id,
                "relevance_note": sel.relevance_note,
                "is_primary": sel.is_primary,
                "claim_text": sel.claim.text if sel.claim else "",
                "claim_type": sel.claim.claim_type if sel.claim else "",
                "is_verified": sel.claim.is_verified if sel.claim else False,
            }
            for sel in item.evidence_selections
        ]
        items_data.append({
            "id": item.id,
            "format": item.format,
            "platform_target": item.platform_target,
            "working_title": item.working_title,
            "angle": item.angle,
            "hook_type": item.hook_type,
            "status": item.status,
            "incremental_cost": item.incremental_cost,
            "manual_time_minutes": item.manual_time_minutes,
            "local_compute_seconds": item.local_compute_seconds,
            "original_value_connection": item.original_value_connection,
            "viewer_value": item.viewer_value,
            "evidence_selections": evidence_data,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        })

    return {
        "id": family.id,
        "title": family.title,
        "slug": family.slug,
        "status": family.status,
        "content_pillar": family.content_pillar,
        "original_value_type": family.original_value_type,
        "summary": family.summary,
        "topic_id": family.topic_id,
        "research_packet_id": family.research_packet_id,
        "originality_plan_id": family.originality_plan_id,
        "primary_experiment_id": family.primary_experiment_id,
        "research_cost": family.research_cost,
        "experiment_cost": family.experiment_cost,
        "ai_cost": family.ai_cost,
        "media_cost": family.media_cost,
        "manual_time_minutes": family.manual_time_minutes,
        "local_compute_seconds": family.local_compute_seconds,
        "economics": economics,
        "items": items_data,
        "created_at": family.created_at.isoformat() if family.created_at else None,
        "updated_at": family.updated_at.isoformat() if family.updated_at else None,
        "approved_at": family.approved_at.isoformat() if family.approved_at else None,
        "archived_at": family.archived_at.isoformat() if family.archived_at else None,
    }


@router.patch("/content-families/{family_id}")
async def update_content_family(
    family_id: str,
    payload: ContentFamilyUpdateInput,
    db: AsyncSession = Depends(get_db),
):
    """Update Content Family fields."""
    repo = ContentFamilyRepository(db)
    updated = await repo.update_family(
        family_id=family_id,
        **payload.model_dump(exclude_unset=True),
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentFamily {family_id} not found",
        )
    return {"id": updated.id, "title": updated.title, "status": updated.status}


@router.post("/content-families/{family_id}/approve")
async def approve_content_family(
    family_id: str,
    payload: ApproveFamilyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve a Content Family to transition into READY_FOR_CONTENT."""
    repo = ContentFamilyRepository(db)
    try:
        family = await repo.approve_family(family_id, reviewer=payload.reviewer or "creator")
        return {
            "id": family.id,
            "status": family.status,
            "approved_at": family.approved_at.isoformat() if family.approved_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/content-families/{family_id}/archive")
async def archive_content_family(
    family_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Archive a Content Family."""
    repo = ContentFamilyRepository(db)
    try:
        family = await repo.archive_family(family_id)
        return {
            "id": family.id,
            "status": family.status,
            "archived_at": family.archived_at.isoformat() if family.archived_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/content-families/{family_id}/suggest-items")
async def suggest_content_items(
    family_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Propose tailored child content items for this family using ContentFamilyEngine."""
    repo = ContentFamilyRepository(db)
    family = await repo.get_family(family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentFamily {family_id} not found",
        )

    # Gather available claims
    evidence_repo = EvidenceRepository(db)
    claims = await evidence_repo.list_claims(packet_id=family.research_packet_id, limit=20)
    claims_payload = [{"id": c.id, "text": c.text} for c in claims]

    engine = engine_registry.get("content_family")
    if not isinstance(engine, ContentFamilyEngine):
        engine = ContentFamilyEngine()

    recent_items = [
        {"hook_type": it.hook_type, "format": it.format}
        for it in family.items
    ]

    what_are_we_adding = ""
    if family.originality_plan:
        what_are_we_adding = family.originality_plan.what_are_we_adding

    proposals_res = engine.suggest_children(
        family_title=family.title,
        topic=family.title,
        originality_type=family.original_value_type,
        what_are_we_adding=what_are_we_adding or family.summary,
        claims=claims_payload,
        content_pillar=family.content_pillar,
        recent_items=recent_items,
    )
    return proposals_res.model_dump()


# ---------------------------------------------------------------------------
# Child Content Item Endpoints
# ---------------------------------------------------------------------------

@router.get("/content-families/{family_id}/items")
async def list_family_items(
    family_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    format_filter: Optional[str] = Query(None, alias="format"),
    platform_target: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List child content items belonging to a family."""
    repo = ContentItemRepository(db)
    items = await repo.list_items(
        content_family_id=family_id,
        status=status_filter,
        format=format_filter,
        platform_target=platform_target,
    )
    return [
        {
            "id": item.id,
            "content_family_id": item.content_family_id,
            "format": item.format,
            "platform_target": item.platform_target,
            "working_title": item.working_title,
            "angle": item.angle,
            "hook_type": item.hook_type,
            "status": item.status,
            "incremental_cost": item.incremental_cost,
            "manual_time_minutes": item.manual_time_minutes,
            "local_compute_seconds": item.local_compute_seconds,
            "original_value_connection": item.original_value_connection,
            "viewer_value": item.viewer_value,
            "evidence_count": len(item.evidence_selections),
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]


@router.post("/content-families/{family_id}/items", status_code=status.HTTP_201_CREATED)
async def create_family_item(
    family_id: str,
    payload: ContentItemCreateInput,
    db: AsyncSession = Depends(get_db),
):
    """Add a new child content item to a Content Family."""
    family_repo = ContentFamilyRepository(db)
    family = await family_repo.get_family(family_id)
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentFamily {family_id} not found",
        )

    # Validate child rules
    engine = engine_registry.get("content_family")
    if not isinstance(engine, ContentFamilyEngine):
        engine = ContentFamilyEngine()

    validation = engine.validate_child(
        child_format=payload.format,
        platform_target=payload.platform_target,
        working_title=payload.working_title,
        angle=payload.angle,
        hook_type=payload.hook_type,
        original_value_connection=payload.original_value_connection,
        claims_count=len(payload.claim_ids),
    )
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Child validation failed: {', '.join(validation.errors)}",
        )

    repo = ContentItemRepository(db)
    try:
        item = await repo.create_item(
            content_family_id=family_id,
            format=payload.format,
            platform_target=payload.platform_target,
            working_title=payload.working_title,
            angle=payload.angle,
            hook_type=payload.hook_type,
            status=payload.status,
            incremental_cost=payload.incremental_cost,
            manual_time_minutes=payload.manual_time_minutes,
            local_compute_seconds=payload.local_compute_seconds,
            original_value_connection=payload.original_value_connection,
            viewer_value=payload.viewer_value,
            claim_ids=payload.claim_ids,
        )
        return {
            "id": item.id,
            "content_family_id": item.content_family_id,
            "format": item.format,
            "platform_target": item.platform_target,
            "working_title": item.working_title,
            "angle": item.angle,
            "hook_type": item.hook_type,
            "status": item.status,
            "incremental_cost": item.incremental_cost,
            "original_value_connection": item.original_value_connection,
            "viewer_value": item.viewer_value,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/content-items/{item_id}")
async def get_content_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get single child content item details."""
    repo = ContentItemRepository(db)
    item = await repo.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentItem {item_id} not found",
        )

    evidence_data = [
        {
            "id": sel.id,
            "claim_id": sel.claim_id,
            "relevance_note": sel.relevance_note,
            "is_primary": sel.is_primary,
            "claim_text": sel.claim.text if sel.claim else "",
            "claim_type": sel.claim.claim_type if sel.claim else "",
            "is_verified": sel.claim.is_verified if sel.claim else False,
        }
        for sel in item.evidence_selections
    ]

    return {
        "id": item.id,
        "content_family_id": item.content_family_id,
        "family_title": item.family.title if item.family else "",
        "format": item.format,
        "platform_target": item.platform_target,
        "working_title": item.working_title,
        "angle": item.angle,
        "hook_type": item.hook_type,
        "status": item.status,
        "script_version_id": item.script_version_id,
        "incremental_cost": item.incremental_cost,
        "manual_time_minutes": item.manual_time_minutes,
        "local_compute_seconds": item.local_compute_seconds,
        "original_value_connection": item.original_value_connection,
        "viewer_value": item.viewer_value,
        "evidence_selections": evidence_data,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.patch("/content-items/{item_id}")
async def update_content_item(
    item_id: str,
    payload: ContentItemUpdateInput,
    db: AsyncSession = Depends(get_db),
):
    """Update child content item properties.
    
    Enforces Phase 11 invariant: child items cannot be set to SCRIPT_APPROVED.
    """
    repo = ContentItemRepository(db)
    try:
        updated = await repo.update_item(
            item_id=item_id,
            **payload.model_dump(exclude_unset=True),
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ContentItem {item_id} not found",
            )
        return {
            "id": updated.id,
            "working_title": updated.working_title,
            "status": updated.status,
            "format": updated.format,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/content-items/{item_id}")
async def delete_content_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a child content item."""
    repo = ContentItemRepository(db)
    success = await repo.delete_item(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentItem {item_id} not found",
        )
    return {"id": item_id, "deleted": True}


@router.post("/content-items/{item_id}/evidence", status_code=status.HTTP_201_CREATED)
async def link_child_evidence(
    item_id: str,
    payload: LinkEvidenceClaimRequest,
    db: AsyncSession = Depends(get_db),
):
    """Link an empirical claim from the Evidence Engine to this child content item."""
    repo = ContentItemRepository(db)
    item = await repo.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentItem {item_id} not found",
        )

    evidence_repo = EvidenceRepository(db)
    claim = await evidence_repo.get_by_id(payload.claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {payload.claim_id} not found",
        )

    sel = await repo.link_evidence(
        content_item_id=item_id,
        claim_id=payload.claim_id,
        relevance_note=payload.relevance_note,
        is_primary=payload.is_primary,
    )
    return {
        "id": sel.id,
        "content_item_id": sel.content_item_id,
        "claim_id": sel.claim_id,
        "relevance_note": sel.relevance_note,
        "is_primary": sel.is_primary,
    }


@router.delete("/content-items/{item_id}/evidence/{claim_id}")
async def unlink_child_evidence(
    item_id: str,
    claim_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Unlink an empirical claim from this child content item."""
    repo = ContentItemRepository(db)
    success = await repo.unlink_evidence(content_item_id=item_id, claim_id=claim_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence link not found",
        )
    return {"content_item_id": item_id, "claim_id": claim_id, "unlinked": True}
