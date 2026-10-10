from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.engines.quality_gate.contracts import (
    CorrectionRoute,
    DimensionStatus,
    FinalApprovalRequest,
    FinalApprovalResponse,
    QualityDimension,
    QualityGateAuditResponse,
)
from app.engines.quality_gate.evaluator import QualityGateEvaluator
from app.models.brand import BrandProfile, SINGLETON_BRAND_ID
from app.models.content_family import ContentFamily, ContentItem
from app.models.media import MediaPackage
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.originality import OriginalityPlan
from app.models.research import ResearchPacket
from app.models.scene import Scene
from app.models.script import ScriptDraft
from app.repositories.quality_gate_repository import QualityGateRepository

router = APIRouter(prefix="/quality-gate", tags=["Quality Gate"])


async def _gather_and_evaluate_item(
    item_id: str,
    db: AsyncSession,
) -> tuple[Dict[str, Any], Optional[ScriptDraft], ContentItem]:
    # 1. Fetch Item with Family
    item_stmt = (
        select(ContentItem)
        .where(ContentItem.id == item_id)
        .options(selectinload(ContentItem.family))
    )
    item_res = await db.execute(item_stmt)
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content item '{item_id}' not found.",
        )

    # 2. Fetch Latest Script
    script_stmt = (
        select(ScriptDraft)
        .where(ScriptDraft.content_item_id == item_id)
        .options(selectinload(ScriptDraft.sections))
        .order_by(ScriptDraft.version.desc())
    )
    script_res = await db.execute(script_stmt)
    script = script_res.scalar_one_or_none()

    # 3. Fetch Research Packet if available
    family = item.family
    packet = None
    if family and family.research_packet_id:
        packet_stmt = (
            select(ResearchPacket)
            .where(ResearchPacket.id == family.research_packet_id)
            .options(selectinload(ResearchPacket.sources), selectinload(ResearchPacket.claims))
        )
        packet_res = await db.execute(packet_stmt)
        packet = packet_res.scalar_one_or_none()

    # 4. Fetch Originality Plan if available
    plan = None
    if family and family.originality_plan_id:
        plan_stmt = select(OriginalityPlan).where(OriginalityPlan.id == family.originality_plan_id)
        plan_res = await db.execute(plan_stmt)
        plan = plan_res.scalar_one_or_none()

    # 5. Fetch Brand & Niche Singletons
    brand_res = await db.execute(select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID))
    brand = brand_res.scalar_one_or_none()

    niche_res = await db.execute(select(NicheProfile).where(NicheProfile.id == SINGLETON_NICHE_ID))
    niche = niche_res.scalar_one_or_none()

    # 6. Fetch Scenes if script exists
    scenes: List[Scene] = []
    if script:
        scene_stmt = (
            select(Scene)
            .where(Scene.script_id == script.id)
            .order_by(Scene.scene_order.asc())
        )
        scenes_res = await db.execute(scene_stmt)
        scenes = list(scenes_res.scalars().all())

    # 7. Fetch Media Package if script exists
    media_pkg = None
    if script:
        pkg_stmt = select(MediaPackage).where(MediaPackage.script_id == script.id)
        pkg_res = await db.execute(pkg_stmt)
        media_pkg = pkg_res.scalar_one_or_none()

    # Run Evaluator
    evaluator = QualityGateEvaluator()
    eval_result = evaluator.evaluate_all(
        item=item,
        script=script,
        family=family,
        packet=packet,
        originality_plan=plan,
        brand=brand,
        niche=niche,
        scenes=scenes,
        media_package=media_pkg,
    )

    return eval_result, script, item


def _format_audit_response(
    audit: Any,
    item: ContentItem,
    script: Optional[ScriptDraft],
    eval_result: Optional[Dict[str, Any]] = None,
) -> QualityGateAuditResponse:
    if eval_result:
        dimensions = eval_result["dimensions"]
        recommendations = eval_result["recommendations"]
        overall_score = eval_result["overall_score"]
        status_val = eval_result["status"]
    else:
        # Reconstruct from audit record
        dimensions = []
        raw_dims = [
            ("evidence_quality", audit.evidence_quality),
            ("brand_fit", audit.brand_fit),
            ("originality", audit.originality),
            ("viewer_value", audit.viewer_value),
            ("niche_fit", audit.niche_fit),
            ("repetition_intelligence", audit.repetition_intelligence),
            ("asset_rights", audit.asset_rights),
            ("media_qc", audit.media_qc),
            ("estimated_cost", audit.estimated_cost),
        ]
        for dim_id, data in raw_dims:
            if data:
                dimensions.append(
                    QualityDimension(
                        id=dim_id,
                        name=data.get("name", dim_id.replace("_", " ").title()),
                        score=data.get("score", 85.0),
                        status=DimensionStatus(data.get("status", "PASSED")),
                        summary=data.get("summary", ""),
                        metrics=data.get("metrics", {}),
                        details=data.get("details", []),
                    )
                )
        recommendations = [
            CorrectionRoute(**r) for r in (audit.actionable_recommendations or [])
        ]
        overall_score = audit.overall_score
        status_val = audit.status

    return QualityGateAuditResponse(
        id=getattr(audit, "id", None),
        content_item_id=item.id,
        script_id=script.id if script else None,
        item_title=item.working_title,
        format=item.format,
        platform_target=item.platform_target,
        status="FINAL_APPROVED" if getattr(audit, "is_approved", False) else status_val,
        overall_score=overall_score,
        is_approved=getattr(audit, "is_approved", False),
        approved_by=getattr(audit, "approved_by", None),
        approved_at=getattr(audit, "approved_at", None),
        override_reason=getattr(audit, "override_reason", None),
        dimensions=dimensions,
        recommendations=recommendations,
        created_at=getattr(audit, "created_at", None),
        updated_at=getattr(audit, "updated_at", None),
    )


@router.get("/item/{item_id}", response_model=QualityGateAuditResponse)
async def get_item_quality_gate(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves or performs the 9-dimension quality gate audit for a content item."""
    repo = QualityGateRepository(db)
    existing = await repo.get_audit_by_item(item_id)

    eval_result, script, item = await _gather_and_evaluate_item(item_id, db)

    # Persist or update audit snapshot
    audit = await repo.create_or_update_audit(
        content_item_id=item_id,
        script_id=script.id if script else None,
        eval_result=eval_result,
    )

    return _format_audit_response(audit, item, script, eval_result)


@router.post("/evaluate/{item_id}", response_model=QualityGateAuditResponse)
async def evaluate_item_quality_gate(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Forces fresh re-evaluation of all 9 creator quality dimensions."""
    eval_result, script, item = await _gather_and_evaluate_item(item_id, db)
    repo = QualityGateRepository(db)
    audit = await repo.create_or_update_audit(
        content_item_id=item_id,
        script_id=script.id if script else None,
        eval_result=eval_result,
    )
    return _format_audit_response(audit, item, script, eval_result)


@router.post("/approve/{item_id}", response_model=FinalApprovalResponse)
async def approve_final_quality_gate(
    item_id: str,
    payload: FinalApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Creator Final Quality Gate: Explicitly approves the item and unlocks export package generation."""
    eval_result, script, item = await _gather_and_evaluate_item(item_id, db)
    repo = QualityGateRepository(db)

    # Check for blocking conditions
    is_blocked = eval_result["status"] == "BLOCKED"
    blocked_dimensions = [
        dimension for dimension in eval_result["dimensions"]
        if dimension.status == DimensionStatus.BLOCKED
    ]
    media_qc_blocked = any(dimension.id == "media_qc" for dimension in blocked_dimensions)
    if media_qc_blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Final Quality Gate Blocked: production media verification failed. "
                "Failed or mock media cannot be approved for export, even with an override reason."
            ),
        )
    if is_blocked and not payload.override_reason:
        blocked_dims = [d.name for d in blocked_dimensions]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Final Quality Gate Blocked: {', '.join(blocked_dims)}. "
                "You must resolve blocking issues or provide an explicit override reason to approve."
            ),
        )

    # Update or create audit first
    await repo.create_or_update_audit(
        content_item_id=item_id,
        script_id=script.id if script else None,
        eval_result=eval_result,
    )

    # Mark as approved
    approved_audit = await repo.approve_audit(
        content_item_id=item_id,
        approved_by=payload.approved_by or "Creator",
        override_reason=payload.override_reason,
    )

    return FinalApprovalResponse(
        content_item_id=item_id,
        script_id=script.id if script else None,
        status="FINAL_APPROVED",
        is_approved=True,
        unlocked_export=True,
        approved_by=approved_audit.approved_by or "Creator",
        approved_at=approved_audit.approved_at or datetime.now(timezone.utc),
        message=f"Final Creator Quality Gate cleared for '{item.working_title}'. Export package generation is now unlocked!",
    )


@router.get("/summary")
async def get_quality_gate_summary(
    db: AsyncSession = Depends(get_db),
):
    """Overview metrics of items pending quality gate review vs approved."""
    items_stmt = select(ContentItem)
    items_res = await db.execute(items_stmt)
    all_items = list(items_res.scalars().all())

    total = len(all_items)
    approved = sum(1 for i in all_items if i.status in ("FINAL_APPROVED", "READY_FOR_EXPORT", "EXPORTED"))
    pending = total - approved

    return {
        "total_items": total,
        "final_approved_count": approved,
        "pending_review_count": pending,
        "approval_rate_percent": round((approved / total * 100), 1) if total > 0 else 0.0,
    }
