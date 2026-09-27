import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.engines.content.engine import ContentEngine
from app.engines.content.contracts import (
    GenerateScriptRequest,
    ScriptDraftOutput,
    ScriptSectionOutput,
    SectionRefineRequest,
    SectionRefineOutput,
    ScriptQualityVerdict,
    RefinementType,
    ScriptApprovalInput,
)
from app.models.content_family import ContentItem, ContentFamily
from app.models.script import ScriptDraft, ScriptSection
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.brand import BrandProfile, SINGLETON_BRAND_ID
from app.models.originality import OriginalityPlan
from app.repositories.content_family_repository import (
    ContentFamilyRepository,
    ContentItemRepository,
)
from app.repositories.script_repository import ScriptRepository

logger = logging.getLogger("studio.api.scripts")

router = APIRouter(prefix="/scripts", tags=["Script Studio"])
engine = ContentEngine()


# Request / Response Schemas
class GenerateScriptPayload(BaseModel):
    content_item_id: str
    target_duration_sec: Optional[int] = None
    guidance: Optional[str] = None


class UpdateSectionPayload(BaseModel):
    heading: Optional[str] = None
    narration: Optional[str] = None
    visual_cue: Optional[str] = None
    linked_claim_ids: Optional[List[str]] = None


class RefineSectionPayload(BaseModel):
    refinement_type: RefinementType
    guidance: Optional[str] = None


class ScriptSectionDetail(BaseModel):
    id: str
    section_type: str
    order_index: int
    heading: str
    narration: str
    visual_cue: str
    estimated_seconds: int
    word_count: int
    linked_claim_ids: List[str]


class ScriptRevisionSummary(BaseModel):
    id: str
    revision_number: int
    trigger: str
    notes: str
    created_at: str


class ScriptDetailResponse(BaseModel):
    id: str
    content_item_id: str
    version: int
    format: str
    title: str
    target_platform: str
    target_duration_sec: int
    total_word_count: int
    estimated_duration_sec: int
    status: str
    is_approved: bool
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    override_reason: Optional[str] = None
    quality_scores: Optional[Dict[str, Any]] = None
    sections: List[ScriptSectionDetail]
    revisions: List[ScriptRevisionSummary] = Field(default_factory=list)


@router.get("/health")
async def get_content_engine_health():
    """Engine health status endpoint."""
    h = engine.health()
    return {
        "status": h.status,
        "engine_id": h.details.get("engine_id", "content"),
        "message": h.message,
        "details": h.details,
    }


@router.post("/generate", response_model=ScriptDetailResponse)
async def generate_script_draft(
    payload: GenerateScriptPayload,
    db: AsyncSession = Depends(get_db),
):
    """Generates an evidence-grounded multi-section script draft for a child content item."""
    item_repo = ContentItemRepository(db)
    script_repo = ScriptRepository(db)

    item = await item_repo.get_item(payload.content_item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentItem {payload.content_item_id} not found.",
        )

    # Load parent family
    family_stmt = select(ContentFamily).where(ContentFamily.id == item.content_family_id)
    f_res = await db.execute(family_stmt)
    family = f_res.scalars().first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent ContentFamily not found.",
        )

    # Load linked evidence claims
    selected_claims = await item_repo.get_selected_claims(item.id)
    claims_data = [
        {
            "id": sc["claim"].id,
            "text": sc["claim"].text,
            "claim_type": sc["claim"].claim_type,
            "is_verified": sc["claim"].is_verified,
            "relevance_note": sc["relevance_note"],
        }
        for sc in selected_claims
    ]

    # Load originality plan
    what_are_we_adding = ""
    if family.originality_plan_id:
        plan = await db.get(OriginalityPlan, family.originality_plan_id)
        if plan:
            what_are_we_adding = plan.what_are_we_adding or ""

    # Load Brand & Niche Profiles
    brand = await db.get(BrandProfile, SINGLETON_BRAND_ID)
    niche = await db.get(NicheProfile, SINGLETON_NICHE_ID)

    target_duration = payload.target_duration_sec or (60 if item.format == "short_vertical" else 600)

    req = GenerateScriptRequest(
        content_item_id=item.id,
        format=item.format,
        working_title=item.working_title,
        angle=item.angle,
        hook_type=item.hook_type,
        platform_target=item.platform_target,
        target_duration_sec=target_duration,
        family_title=family.title,
        content_pillar=family.content_pillar,
        original_value_type=family.original_value_type,
        what_are_we_adding=what_are_we_adding or item.original_value_connection,
        evidence_claims=claims_data,
        brand_tone=brand.tone if brand else ["Direct", "Empirical", "Technical"],
        banned_cliches=brand.banned_cliches if brand else [],
        voice_rules=brand.voice_rules if brand else [],
        cta_style=brand.cta_style if brand else "soft_value",
        niche_allowed_topics=niche.allowed_topics if niche else [],
        niche_blocked_topics=niche.blocked_topics if niche else [],
    )

    draft_output = engine.generate_script(req)

    # Persist in DB
    # Check if a draft already exists for this item
    existing = await script_repo.get_by_content_item(item.id)
    version = (existing.version + 1) if existing else 1

    script = await script_repo.create_script(
        content_item_id=item.id,
        format=item.format,
        title=item.working_title,
        target_platform=item.platform_target,
        target_duration_sec=target_duration,
        version=version,
    )

    # Add sections
    for sec in draft_output.sections:
        await script_repo.add_section(
            script_id=script.id,
            section_type=sec.section_type,
            order_index=sec.order_index,
            heading=sec.heading,
            narration=sec.narration,
            visual_cue=sec.visual_cue,
            estimated_seconds=sec.estimated_seconds,
            word_count=sec.word_count,
            linked_claim_ids=sec.linked_claim_ids,
        )

    # Save initial revision
    await script_repo.create_revision(
        script_id=script.id,
        trigger="initial_generation",
        notes=f"Initial evidence-grounded script generated ({item.format})",
    )

    # Update quality scores on script
    if draft_output.quality_verdict:
        await script_repo.update_quality_scores(
            script.id, draft_output.quality_verdict.model_dump()
        )

    # Transition ContentItem to SCRIPT_REVIEW
    await item_repo.update_item(
        item.id,
        status="SCRIPT_REVIEW",
        script_version_id=script.id,
    )

    refreshed = await script_repo.get_script(script.id)
    return _build_script_response(refreshed)


@router.get("/{script_id}", response_model=ScriptDetailResponse)
async def get_script_detail(
    script_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full script draft with sections, revisions, and quality metrics."""
    script_repo = ScriptRepository(db)
    script = await script_repo.get_script(script_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script {script_id} not found.",
        )
    return _build_script_response(script)


@router.get("/item/{content_item_id}", response_model=ScriptDetailResponse)
async def get_script_by_item(
    content_item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves active script draft for a specific child content item."""
    script_repo = ScriptRepository(db)
    script = await script_repo.get_by_content_item(content_item_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No script draft generated for content item {content_item_id} yet.",
        )
    return _build_script_response(script)


@router.patch("/{script_id}/sections/{section_id}", response_model=ScriptDetailResponse)
async def update_script_section(
    script_id: str,
    section_id: str,
    payload: UpdateSectionPayload,
    db: AsyncSession = Depends(get_db),
):
    """Updates section narration, visual cues, or linked claims and creates a revision checkpoint."""
    script_repo = ScriptRepository(db)
    script = await script_repo.get_script(script_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script {script_id} not found.",
        )

    updates = {}
    if payload.heading is not None:
        updates["heading"] = payload.heading
    if payload.narration is not None:
        updates["narration"] = payload.narration
    if payload.visual_cue is not None:
        updates["visual_cue"] = payload.visual_cue
    if payload.linked_claim_ids is not None:
        updates["linked_claim_ids"] = payload.linked_claim_ids

    sec = await script_repo.update_section(section_id, **updates)
    if not sec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section {section_id} not found.",
        )

    # Record revision
    await script_repo.create_revision(
        script_id=script_id,
        trigger="manual_edit",
        notes=f"Edited {sec.section_type} section",
        section_id=section_id,
    )

    # Re-evaluate quality scores
    await _recalculate_quality(script_id, db)

    refreshed = await script_repo.get_script(script_id)
    return _build_script_response(refreshed)


@router.post("/{script_id}/sections/{section_id}/refine")
async def refine_script_section(
    script_id: str,
    section_id: str,
    payload: RefineSectionPayload,
    db: AsyncSession = Depends(get_db),
):
    """Executes section refinement (shorten, expand, make_clearer, more_evidence, regenerate)."""
    script_repo = ScriptRepository(db)
    script = await script_repo.get_script(script_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script {script_id} not found.",
        )

    sec = next((s for s in script.sections if s.id == section_id), None)
    if not sec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section {section_id} not found.",
        )

    # Load claims
    item_repo = ContentItemRepository(db)
    claims = await item_repo.get_selected_claims(script.content_item_id)
    claims_data = [{"text": c["claim"].text} for c in claims]

    brand = await db.get(BrandProfile, SINGLETON_BRAND_ID)

    refine_req = SectionRefineRequest(
        script_id=script_id,
        section_id=section_id,
        section_type=sec.section_type,
        current_narration=sec.narration,
        current_visual_cue=sec.visual_cue,
        refinement_type=payload.refinement_type,
        guidance=payload.guidance,
        linked_claims=claims_data,
        brand_tone=brand.tone if brand else [],
    )

    result = engine.refine_section(refine_req)

    # Update in DB
    await script_repo.update_section(
        section_id,
        narration=result.new_narration,
        visual_cue=result.new_visual_cue,
        word_count=result.word_count,
        estimated_seconds=result.estimated_seconds,
    )

    # Record revision
    await script_repo.create_revision(
        script_id=script_id,
        trigger=payload.refinement_type.value,
        notes=f"Refined section ({payload.refinement_type.value}): {result.explanation}",
        section_id=section_id,
    )

    # Re-evaluate quality
    await _recalculate_quality(script_id, db)

    refreshed = await script_repo.get_script(script_id)
    return {
        "refinement": result.model_dump(),
        "script": _build_script_response(refreshed),
    }


@router.post("/{script_id}/quality-check", response_model=ScriptQualityVerdict)
async def check_script_quality(
    script_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Runs the 6-dimension quality check on current script draft."""
    verdict = await _recalculate_quality(script_id, db)
    return verdict


@router.post("/{script_id}/approve", response_model=ScriptDetailResponse)
async def approve_script_quality_gate(
    script_id: str,
    payload: ScriptApprovalInput,
    db: AsyncSession = Depends(get_db),
):
    """Creator Human Quality Gate: approves script draft and transitions child item to SCRIPT_APPROVED."""
    script_repo = ScriptRepository(db)
    script = await script_repo.get_script(script_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script {script_id} not found.",
        )

    # Run fresh quality check
    verdict = await _recalculate_quality(script_id, db)

    # Check blocking gates
    if not verdict.is_approvable and not payload.override_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Script approval rejected by quality gate.",
                "blocking_reasons": verdict.blocking_reasons,
                "summary": verdict.summary,
                "help": "Provide an explicit 'override_reason' if you wish to bypass this warning.",
            },
        )

    approved = await script_repo.approve_script(
        script_id=script_id,
        reviewer=payload.reviewer,
        override_reason=payload.override_reason,
    )
    return _build_script_response(approved)


@router.get("/{script_id}/revisions", response_model=List[ScriptRevisionSummary])
async def list_script_revisions(
    script_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Lists revision history audit trail for undo and review."""
    script_repo = ScriptRepository(db)
    script = await script_repo.get_script(script_id)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script {script_id} not found.",
        )
    return [
        ScriptRevisionSummary(
            id=r.id,
            revision_number=r.revision_number,
            trigger=r.trigger,
            notes=r.notes,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in script.revisions
    ]


@router.post("/{script_id}/revisions/{revision_id}/restore", response_model=ScriptDetailResponse)
async def restore_script_revision(
    script_id: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Restores script content to a historical revision snapshot."""
    script_repo = ScriptRepository(db)
    restored = await script_repo.restore_revision(script_id, revision_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision or script not found.",
        )
    await _recalculate_quality(script_id, db)
    refreshed = await script_repo.get_script(script_id)
    return _build_script_response(refreshed)


async def _recalculate_quality(script_id: str, db: AsyncSession) -> ScriptQualityVerdict:
    script_repo = ScriptRepository(db)
    script = await script_repo.get_script(script_id)
    if not script:
        raise ValueError(f"Script {script_id} not found.")

    item_repo = ContentItemRepository(db)
    item = await item_repo.get_item(script.content_item_id)
    family_stmt = select(ContentFamily).where(ContentFamily.id == item.content_family_id)
    f_res = await db.execute(family_stmt)
    family = f_res.scalars().first()

    claims = await item_repo.get_selected_claims(item.id)
    claims_data = [{"id": c["claim"].id, "text": c["claim"].text} for c in claims]

    brand = await db.get(BrandProfile, SINGLETON_BRAND_ID)
    niche = await db.get(NicheProfile, SINGLETON_NICHE_ID)

    sec_stmt = (
        select(ScriptSection)
        .where(ScriptSection.script_id == script_id)
        .order_by(ScriptSection.order_index)
    )
    sec_res = await db.execute(sec_stmt)
    db_sections = list(sec_res.scalars().all())

    sec_outputs = [
        ScriptSectionOutput(
            id=s.id,
            section_type=s.section_type,
            order_index=s.order_index,
            heading=s.heading,
            narration=s.narration,
            visual_cue=s.visual_cue,
            estimated_seconds=s.estimated_seconds,
            word_count=s.word_count,
            linked_claim_ids=s.linked_claim_ids or [],
        )
        for s in db_sections
    ]

    banned_list = (brand.banned_cliches if (brand and brand.banned_cliches) else None)

    req = GenerateScriptRequest(
        content_item_id=item.id,
        format=script.format,
        working_title=script.title,
        angle=item.angle,
        family_title=family.title if family else "",
        content_pillar=family.content_pillar if family else "Core",
        original_value_type=family.original_value_type if family else "benchmark",
        what_are_we_adding=item.original_value_connection,
        evidence_claims=claims_data,
        brand_tone=brand.tone if brand else [],
        banned_cliches=banned_list or [],
        niche_allowed_topics=niche.allowed_topics if niche else [],
        niche_blocked_topics=niche.blocked_topics if niche else [],
    )

    verdict = engine.evaluate_quality(sec_outputs, req)
    await script_repo.update_quality_scores(script.id, verdict.model_dump())
    return verdict


def _build_script_response(script) -> ScriptDetailResponse:
    return ScriptDetailResponse(
        id=script.id,
        content_item_id=script.content_item_id,
        version=script.version,
        format=script.format,
        title=script.title,
        target_platform=script.target_platform,
        target_duration_sec=script.target_duration_sec,
        total_word_count=script.total_word_count,
        estimated_duration_sec=script.estimated_duration_sec,
        status=script.status,
        is_approved=script.is_approved,
        approved_by=script.approved_by,
        approved_at=script.approved_at.isoformat() if script.approved_at else None,
        override_reason=script.override_reason,
        quality_scores=script.quality_scores,
        sections=[
            ScriptSectionDetail(
                id=s.id,
                section_type=s.section_type,
                order_index=s.order_index,
                heading=s.heading,
                narration=s.narration,
                visual_cue=s.visual_cue,
                estimated_seconds=s.estimated_seconds,
                word_count=s.word_count,
                linked_claim_ids=s.linked_claim_ids or [],
            )
            for s in sorted(script.sections, key=lambda x: x.order_index)
        ],
        revisions=[
            ScriptRevisionSummary(
                id=r.id,
                revision_number=r.revision_number,
                trigger=r.trigger,
                notes=r.notes,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in (script.revisions or [])
        ],
    )
