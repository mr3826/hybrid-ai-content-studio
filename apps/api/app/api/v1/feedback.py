import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.engines.core.base import EngineContext
from app.engines.core.registry import engine_registry
from app.engines.feedback.contracts import (
    FeedbackActionRequest,
    FeedbackEvaluateRequest,
    FeedbackEvaluateResponse,
    FeedbackExplainResponse,
    FeedbackLessonCreateRequest,
    FeedbackLessonResponse,
    FeedbackSummaryResponse,
)
from app.models.analytics import PublicationMetricsSnapshot
from app.models.brand import BrandProfile, SINGLETON_BRAND_ID
from app.models.content_family import ContentItem
from app.models.feedback import FeedbackLesson
from app.models.script import ScriptDraft
from app.repositories.feedback_repository import FeedbackRepository

router = APIRouter(prefix="/feedback", tags=["Feedback"])


def _map_lesson_to_response(lesson: FeedbackLesson, content_item_title: Optional[str] = None) -> FeedbackLessonResponse:
    title = content_item_title
    if not title and lesson.content_item:
        title = lesson.content_item.working_title
    return FeedbackLessonResponse(
        id=lesson.id,
        content_item_id=lesson.content_item_id,
        content_item_title=title,
        lesson_type=lesson.lesson_type,
        title=lesson.title,
        observation=lesson.observation,
        impact_level=lesson.impact_level,
        confidence_score=lesson.confidence_score,
        evidence_data=lesson.evidence_data or {},
        proposed_adjustment=lesson.proposed_adjustment or {},
        status=lesson.status,
        creator_notes=lesson.creator_notes,
        reviewed_at=lesson.reviewed_at,
        applied_at=lesson.applied_at,
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )


@router.get("/summary", response_model=FeedbackSummaryResponse)
async def get_feedback_summary(
    db: AsyncSession = Depends(get_db),
):
    """Returns summary KPIs of all feedback lessons and closed loop status."""
    repo = FeedbackRepository(db)
    summary = await repo.get_feedback_summary()
    return FeedbackSummaryResponse(**summary)


@router.get("/lessons", response_model=List[FeedbackLessonResponse])
async def list_feedback_lessons(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED, APPLIED)"),
    lesson_type: Optional[str] = Query(None, description="Filter by lesson type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List feedback lessons with optional filtering."""
    repo = FeedbackRepository(db)
    lessons = await repo.list_lessons(status=status, lesson_type=lesson_type, limit=limit, offset=offset)
    return [_map_lesson_to_response(l) for l in lessons]


@router.get("/lessons/{lesson_id}", response_model=FeedbackLessonResponse)
async def get_feedback_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch single feedback lesson details."""
    repo = FeedbackRepository(db)
    lesson = await repo.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Feedback lesson not found")
    return _map_lesson_to_response(lesson)


@router.post("/lessons", response_model=FeedbackLessonResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_lesson(
    payload: FeedbackLessonCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually log a creator lesson or strategic observation."""
    repo = FeedbackRepository(db)
    lesson = await repo.create_lesson(payload.model_dump())
    return _map_lesson_to_response(lesson)


@router.post("/lessons/{lesson_id}/approve", response_model=FeedbackLessonResponse)
async def approve_feedback_lesson(
    lesson_id: str,
    payload: FeedbackActionRequest = FeedbackActionRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Creator Approval Gate: Approve a proposed feedback lesson."""
    repo = FeedbackRepository(db)
    lesson = await repo.approve_lesson(lesson_id, creator_notes=payload.creator_notes)
    if not lesson:
        raise HTTPException(status_code=404, detail="Feedback lesson not found")
    return _map_lesson_to_response(lesson)


@router.post("/lessons/{lesson_id}/reject", response_model=FeedbackLessonResponse)
async def reject_feedback_lesson(
    lesson_id: str,
    payload: FeedbackActionRequest = FeedbackActionRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Creator Quality Gate: Reject a proposed feedback lesson."""
    repo = FeedbackRepository(db)
    lesson = await repo.reject_lesson(lesson_id, creator_notes=payload.creator_notes)
    if not lesson:
        raise HTTPException(status_code=404, detail="Feedback lesson not found")
    return _map_lesson_to_response(lesson)


@router.post("/lessons/{lesson_id}/apply", response_model=FeedbackLessonResponse)
async def apply_feedback_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Human-Approved Apply Gate: Apply an approved lesson directly to Brand DNA (BrandProfile / BrandMemoryItem / BrandExemplar)."""
    repo = FeedbackRepository(db)
    lesson = await repo.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Feedback lesson not found")
    if lesson.status == "REJECTED":
        raise HTTPException(status_code=400, detail="Cannot apply a rejected lesson")
    
    updated_lesson = await repo.apply_lesson(lesson_id)
    return _map_lesson_to_response(updated_lesson)


@router.post("/evaluate", response_model=FeedbackEvaluateResponse)
async def evaluate_performance_feedback(
    payload: FeedbackEvaluateRequest = FeedbackEvaluateRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Run Feedback Engine to synthesize performance lessons from recent publication metrics."""
    # 1. Fetch recent publication metrics snapshots
    snap_stmt = select(PublicationMetricsSnapshot).order_by(PublicationMetricsSnapshot.snapshot_timestamp.desc()).limit(100)
    snap_res = await db.execute(snap_stmt)
    snapshots = list(snap_res.scalars().all())

    # 2. Fetch associated content items and scripts
    content_item_ids = list(set(s.content_item_id for s in snapshots if s.content_item_id))
    content_items_map: Dict[str, Any] = {}
    scripts_map: Dict[str, Any] = {}

    if content_item_ids:
        c_stmt = select(ContentItem).where(ContentItem.id.in_(content_item_ids))
        c_res = await db.execute(c_stmt)
        for c in c_res.scalars().all():
            content_items_map[c.id] = {"id": c.id, "working_title": c.working_title}

        s_stmt = select(ScriptDraft).where(ScriptDraft.content_item_id.in_(content_item_ids)).options(selectinload(ScriptDraft.sections))
        s_res = await db.execute(s_stmt)
        for s in s_res.scalars().all():
            hook_text = ""
            for sec in s.sections:
                if sec.section_type == "hook":
                    hook_text = sec.narration
                    break
            scripts_map[s.content_item_id] = {"hook_text": hook_text}

    # 3. Fetch BrandProfile
    b_stmt = select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID)
    b_res = await db.execute(b_stmt)
    brand = b_res.scalar_one_or_none()
    brand_dict = {
        "avoid_vocabulary": getattr(brand, "avoid_vocabulary", []) if brand else [],
        "banned_cliches": getattr(brand, "banned_cliches", []) if brand else [],
        "preferred_vocabulary": getattr(brand, "preferred_vocabulary", []) if brand else [],
    }

    # 4. Prepare snapshots dict list
    snapshots_data = [
        {
            "id": s.id,
            "content_item_id": s.content_item_id,
            "platform": s.platform,
            "views": s.views,
            "impressions": s.impressions,
            "likes": s.likes,
            "comments": s.comments,
            "shares": s.shares,
            "saves": s.saves,
            "hook_retention_3s_pct": s.hook_retention_3s_pct,
            "retention_rate_pct": s.retention_rate_pct,
        }
        for s in snapshots
    ]

    # 5. Run Feedback Engine
    engine = engine_registry.get("feedback")
    if not engine:
        raise HTTPException(status_code=500, detail="Feedback Engine not registered in engine registry")

    context = EngineContext(
        run_id=str(uuid.uuid4()),
        parameters={
            "snapshots": snapshots_data,
            "content_items_map": content_items_map,
            "scripts_map": scripts_map,
            "brand_profile": brand_dict,
        },
    )
    result = await engine.run(context)
    generated_lessons_raw = result.outputs

    # 6. Save new proposed lessons into DB (checking existing by observation / title)
    repo = FeedbackRepository(db)
    saved_lessons = []
    for l_raw in generated_lessons_raw:
        # Check if already exists with same title & content_item_id
        existing_stmt = select(FeedbackLesson).where(
            FeedbackLesson.title == l_raw["title"],
            FeedbackLesson.content_item_id == l_raw.get("content_item_id"),
        )
        existing_res = await db.execute(existing_stmt)
        if existing_res.scalar_one_or_none():
            continue

        created = await repo.create_lesson(l_raw)
        title = (content_items_map.get(created.content_item_id) or {}).get("working_title")
        saved_lessons.append(_map_lesson_to_response(created, content_item_title=title))

    return FeedbackEvaluateResponse(
        evaluated_snapshots=len(snapshots_data),
        lessons_generated=len(saved_lessons),
        lessons=saved_lessons,
    )


@router.get("/explain/{lesson_id}", response_model=FeedbackExplainResponse)
async def explain_feedback_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Explains the evidence-based reasoning and human-gate policy for a given lesson."""
    repo = FeedbackRepository(db)
    lesson = await repo.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Feedback lesson not found")

    engine = engine_registry.get("feedback")
    explanation = engine.explain(lesson.id) if engine else None

    return FeedbackExplainResponse(
        lesson_id=lesson.id,
        lesson_type=lesson.lesson_type,
        title=lesson.title,
        observation=lesson.observation,
        reasoning=f"Identified from publication performance metrics on {lesson.evidence_data.get('platform', 'published content')}. Confidence score: {lesson.confidence_score:.2f}.",
        data_source="PublicationMetricsSnapshot & ScriptDraft",
        rule_triggered=f"Threshold rule: {lesson.lesson_type}",
        human_gate_required=True,
    )
