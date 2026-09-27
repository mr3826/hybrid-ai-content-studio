import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.registry import engine_registry
from app.engines.originality.contracts import (
    CreateAttachmentRequest,
    CreateExperimentRequest,
    CreatePlanRequest,
    OriginalityType,
)
from app.engines.originality.engine import OriginalityEngine
from app.models.originality import OriginalityPlan
from app.repositories.originality_repository import (
    OriginalityRepository,
    SUPPORTED_ORIGINALITY_TYPES,
)

router = APIRouter(prefix="/originality", tags=["originality"])


class ApprovePlanRequest(BaseModel):
    reviewer: Optional[str] = Field("creator", description="Reviewer name or identifier")
    notes: Optional[str] = Field(None, description="Approval notes")


class RejectPlanRequest(BaseModel):
    reason: str = Field(..., description="Explanation for rejection")


class ProposeAnglesRequest(BaseModel):
    topic: str = Field(..., description="Topic or headline to propose original angles for")
    summary: Optional[str] = Field("", description="Optional background context or summary")


class LinkEvidenceRequest(BaseModel):
    conclusion_text: str = Field(..., description="Synthesis conclusion to record in Evidence Engine")
    claim_id: Optional[str] = Field(None, description="Optional claim ID to link to")
    confidence: float = Field(0.95, description="Confidence score from 0.0 to 1.0")


ORIGINALITY_FORMAT_DESCRIPTIONS = {
    "tool_test": "Hands-on testing of an AI tool, software, or library on local hardware with documented setup and results.",
    "benchmark": "Rigorous quantitative side-by-side performance, speed, latency, or memory usage comparison.",
    "cost_comparison": "Real-world financial analysis comparing local self-hosted costs against cloud API pricing.",
    "workflow_demonstration": "Live walkthrough integrating multiple local tools into an automated end-to-end pipeline.",
    "before_after": "Direct comparison showing baseline performance versus optimized or fine-tuned configuration.",
    "implementation_attempt": "Authentic attempt to build or deploy a new model, documenting every step and blocker encountered.",
    "multi_source_synthesis": "Comprehensive cross-reference of documentation, community findings, and real developer experiences.",
    "original_framework": "A novel mental model, categorization system, or decision tree created specifically for our audience.",
    "original_chart_data_analysis": "Custom chart, graph, or dataset visualization synthesizing empirical metrics.",
    "practical_tutorial": "Reproducible, terminal-verified, step-by-step tutorial with copy-pasteable commands and configs.",
    "failure_analysis": "Diagnostic breakdown of why a tool or setup failed, crashes, or produces degraded outputs.",
    "clearly_labeled_opinion": "Explicit editorial thesis with stated assumptions, distinct from empirical benchmark facts.",
}


@router.get("/health")
async def originality_health():
    """Health check for Originality Engine."""
    engine = engine_registry.get("originality")
    if engine:
        return engine.health()
    return {"status": "unregistered", "engine_id": "originality"}


@router.get("/formats")
async def list_originality_formats():
    """List the 12 recognized originality formats with descriptions."""
    formats = []
    for fmt in SUPPORTED_ORIGINALITY_TYPES:
        formats.append({
            "type": fmt,
            "title": fmt.replace("_", " ").title(),
            "description": ORIGINALITY_FORMAT_DESCRIPTIONS.get(fmt, ""),
        })
    return {"formats": formats, "count": len(formats)}


@router.post("/propose-angles")
async def propose_original_angles(payload: ProposeAnglesRequest):
    """Propose 3 concrete original contribution angles for an opportunity topic."""
    engine = engine_registry.get("originality")
    if isinstance(engine, OriginalityEngine):
        angles = engine.propose_original_angles(payload.topic, payload.summary or "")
    else:
        temp_engine = OriginalityEngine()
        angles = temp_engine.propose_original_angles(payload.topic, payload.summary or "")

    return {"topic": payload.topic, "angles": angles}


@router.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: CreatePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create an originality plan enforcing 'What are WE adding?' quality gates.
    
    Generic summaries automatically default to 'not_ready' and cannot pass human approval.
    """
    repo = OriginalityRepository(db)
    plan = await repo.create_plan(
        topic=payload.topic,
        originality_type=payload.originality_type,
        what_are_we_adding=payload.what_are_we_adding,
        why_it_matters=payload.why_it_matters,
        opportunity_id=payload.opportunity_id,
        packet_id=payload.packet_id,
        suggested_experiments=payload.suggested_experiments,
    )
    return {
        "id": plan.id,
        "topic": plan.topic,
        "slug": plan.slug,
        "originality_type": plan.originality_type,
        "what_are_we_adding": plan.what_are_we_adding,
        "why_it_matters": plan.why_it_matters,
        "status": plan.status,
        "is_generic_summary": plan.is_generic_summary,
        "confidence_score": plan.confidence_score,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


@router.get("/plans")
async def list_plans(
    status_filter: Optional[str] = Query(None, alias="status"),
    originality_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List originality plans with optional filtering."""
    repo = OriginalityRepository(db)
    plans = await repo.list_plans(
        status=status_filter,
        originality_type=originality_type,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": p.id,
            "topic": p.topic,
            "slug": p.slug,
            "originality_type": p.originality_type,
            "what_are_we_adding": p.what_are_we_adding,
            "why_it_matters": p.why_it_matters,
            "status": p.status,
            "is_generic_summary": p.is_generic_summary,
            "confidence_score": p.confidence_score,
            "opportunity_id": p.opportunity_id,
            "reviewed_by": p.reviewed_by,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full details of an originality plan including linked experiments."""
    repo = OriginalityRepository(db)
    plan = await repo.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OriginalityPlan {plan_id} not found",
        )

    experiments_data = []
    for exp in plan.experiments:
        attachments_data = [
            {
                "id": a.id,
                "attachment_type": a.attachment_type,
                "filename": a.filename,
                "file_path": a.file_path,
                "mime_type": a.mime_type,
                "size_bytes": a.size_bytes,
                "caption": a.caption,
            }
            for a in exp.attachments
        ]
        conclusions_data = [
            {
                "id": c.id,
                "summary": c.summary,
                "confidence": c.confidence,
                "claim_id": c.claim_id,
            }
            for c in exp.conclusions
        ]
        experiments_data.append({
            "id": exp.id,
            "title": exp.title,
            "question": exp.question,
            "hypothesis": exp.hypothesis,
            "method": exp.method,
            "dataset_sample": exp.dataset_sample,
            "tools_models": exp.tools_models,
            "parameters": exp.parameters,
            "results": exp.results,
            "failures": exp.failures,
            "latency_ms": exp.latency_ms,
            "cost_usd": exp.cost_usd,
            "notes": exp.notes,
            "conclusion": exp.conclusion,
            "status": exp.status,
            "attachments": attachments_data,
            "conclusions": conclusions_data,
        })

    return {
        "id": plan.id,
        "topic": plan.topic,
        "slug": plan.slug,
        "originality_type": plan.originality_type,
        "what_are_we_adding": plan.what_are_we_adding,
        "why_it_matters": plan.why_it_matters,
        "status": plan.status,
        "is_generic_summary": plan.is_generic_summary,
        "confidence_score": plan.confidence_score,
        "opportunity_id": plan.opportunity_id,
        "packet_id": plan.packet_id,
        "reviewed_by": plan.reviewed_by,
        "review_notes": plan.review_notes,
        "reviewed_at": plan.reviewed_at.isoformat() if plan.reviewed_at else None,
        "suggested_experiments": plan.suggested_experiments,
        "experiments": experiments_data,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


@router.post("/plans/{plan_id}/approve")
async def approve_plan(
    plan_id: str,
    payload: ApprovePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Human Quality Gate: Approve an originality plan.
    
    CRITICAL: Generic summaries CANNOT be approved under studio invariants.
    """
    repo = OriginalityRepository(db)
    try:
        plan = await repo.approve_plan(
            plan_id=plan_id,
            reviewer=payload.reviewer or "creator",
            notes=payload.notes,
        )
        return {
            "id": plan.id,
            "status": plan.status,
            "reviewed_by": plan.reviewed_by,
            "review_notes": plan.review_notes,
            "reviewed_at": plan.reviewed_at.isoformat() if plan.reviewed_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/plans/{plan_id}/reject")
async def reject_plan(
    plan_id: str,
    payload: RejectPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Human Quality Gate: Reject an originality plan."""
    repo = OriginalityRepository(db)
    try:
        plan = await repo.reject_plan(
            plan_id=plan_id,
            reason=payload.reason,
        )
        return {
            "id": plan.id,
            "status": plan.status,
            "review_notes": plan.review_notes,
            "reviewed_at": plan.reviewed_at.isoformat() if plan.reviewed_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ---------------------------------------------------------------------------
# Experiment Workspace Endpoints
# ---------------------------------------------------------------------------

@router.post("/experiments", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: CreateExperimentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create an empirical experiment in the workspace."""
    repo = OriginalityRepository(db)
    exp = await repo.create_experiment(
        title=payload.title,
        hypothesis=payload.hypothesis,
        method=payload.method,
        question=payload.question,
        dataset_sample=payload.dataset_sample,
        tools_models=payload.tools_models,
        parameters=payload.parameters,
        results=payload.results,
        failures=payload.failures,
        latency_ms=payload.latency_ms,
        cost_usd=payload.cost_usd,
        screenshots_files=payload.screenshots_files,
        notes=payload.notes,
        conclusion=payload.conclusion,
        status=payload.status,
        opportunity_id=payload.opportunity_id,
        originality_plan_id=payload.originality_plan_id,
    )
    return {
        "id": exp.id,
        "title": exp.title,
        "question": exp.question,
        "hypothesis": exp.hypothesis,
        "method": exp.method,
        "dataset_sample": exp.dataset_sample,
        "tools_models": exp.tools_models,
        "parameters": exp.parameters,
        "results": exp.results,
        "failures": exp.failures,
        "latency_ms": exp.latency_ms,
        "cost_usd": exp.cost_usd,
        "notes": exp.notes,
        "conclusion": exp.conclusion,
        "status": exp.status,
        "opportunity_id": exp.opportunity_id,
        "originality_plan_id": exp.originality_plan_id,
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
    }


@router.get("/experiments")
async def list_experiments(
    opportunity_id: Optional[str] = Query(None),
    originality_plan_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List experiments in the workspace."""
    repo = OriginalityRepository(db)
    experiments = await repo.list_experiments(
        opportunity_id=opportunity_id,
        originality_plan_id=originality_plan_id,
        status=status_filter,
        limit=limit,
    )
    return [
        {
            "id": exp.id,
            "title": exp.title,
            "question": exp.question,
            "hypothesis": exp.hypothesis,
            "method": exp.method,
            "dataset_sample": exp.dataset_sample,
            "tools_models": exp.tools_models,
            "results": exp.results,
            "failures": exp.failures,
            "latency_ms": exp.latency_ms,
            "cost_usd": exp.cost_usd,
            "conclusion": exp.conclusion,
            "status": exp.status,
            "originality_plan_id": exp.originality_plan_id,
            "opportunity_id": exp.opportunity_id,
            "attachment_count": len(exp.attachments) if exp.attachments else 0,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
        }
        for exp in experiments
    ]


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get experiment details with attachments, runs, and linked conclusions."""
    repo = OriginalityRepository(db)
    exp = await repo.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    attachments_data = [
        {
            "id": a.id,
            "attachment_type": a.attachment_type,
            "filename": a.filename,
            "file_path": a.file_path,
            "mime_type": a.mime_type,
            "size_bytes": a.size_bytes,
            "content_snippet": a.content_snippet,
            "caption": a.caption,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in exp.attachments
    ]

    conclusions_data = [
        {
            "id": c.id,
            "summary": c.summary,
            "confidence": c.confidence,
            "claim_id": c.claim_id,
        }
        for c in exp.conclusions
    ]

    return {
        "id": exp.id,
        "title": exp.title,
        "question": exp.question,
        "hypothesis": exp.hypothesis,
        "method": exp.method,
        "dataset_sample": exp.dataset_sample,
        "tools_models": exp.tools_models,
        "parameters": exp.parameters,
        "results": exp.results,
        "failures": exp.failures,
        "latency_ms": exp.latency_ms,
        "cost_usd": exp.cost_usd,
        "notes": exp.notes,
        "conclusion": exp.conclusion,
        "status": exp.status,
        "opportunity_id": exp.opportunity_id,
        "originality_plan_id": exp.originality_plan_id,
        "attachments": attachments_data,
        "conclusions": conclusions_data,
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
    }


@router.post("/experiments/{experiment_id}/attachments", status_code=status.HTTP_201_CREATED)
async def add_attachment(
    experiment_id: str,
    payload: CreateAttachmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Attach artifacts (JSON, CSV, screenshots, code snippets) to an experiment."""
    repo = OriginalityRepository(db)
    exp = await repo.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    att = await repo.add_attachment(
        experiment_id=experiment_id,
        attachment_type=payload.attachment_type,
        filename=payload.filename,
        file_path=payload.file_path,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        content_snippet=payload.content_snippet,
        caption=payload.caption,
    )
    return {
        "id": att.id,
        "experiment_id": att.experiment_id,
        "attachment_type": att.attachment_type,
        "filename": att.filename,
        "file_path": att.file_path,
        "mime_type": att.mime_type,
        "size_bytes": att.size_bytes,
        "content_snippet": att.content_snippet,
        "caption": att.caption,
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }


@router.post("/experiments/{experiment_id}/link-evidence", status_code=status.HTTP_201_CREATED)
async def link_to_evidence(
    experiment_id: str,
    payload: LinkEvidenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Link quantitative experiment results to the Evidence Engine provenance graph."""
    repo = OriginalityRepository(db)
    exp = await repo.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    conclusion = await repo.link_to_evidence(
        experiment_id=experiment_id,
        claim_id=payload.claim_id,
        conclusion_text=payload.conclusion_text,
        confidence=payload.confidence,
    )
    return {
        "id": conclusion.id,
        "experiment_id": conclusion.experiment_id,
        "claim_id": conclusion.claim_id,
        "summary": conclusion.summary,
        "confidence": conclusion.confidence,
    }
