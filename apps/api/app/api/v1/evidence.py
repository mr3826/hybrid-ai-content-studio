import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.base import EngineContext, EngineResult
from app.engines.evidence.contracts import (
    AddConclusionInput,
    AddRunInput,
    CoverageReport,
    CreateClaimInput,
    CreateExperimentInput,
    EvidenceEngineInput,
    LabelOpinionInput,
    LinkEvidenceInput,
    OverrideClaimInput,
    ProvenanceTrace,
)
from app.engines.evidence.engine import EvidenceEngine
from app.engines.core.registry import engine_registry
from app.models.evidence import (
    Claim,
    ClaimEvidence,
    Conclusion,
    ContentClaim,
    EvidenceSource,
    Experiment,
    ExperimentRun,
)
from app.repositories.evidence_repository import EvidenceRepository

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/health")
async def evidence_health():
    """Health check for Evidence Engine."""
    engine = engine_registry.get("evidence")
    if engine:
        return engine.health()
    return {"status": "unregistered", "engine_id": "evidence"}


@router.post("/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(
    payload: CreateClaimInput,
    db: AsyncSession = Depends(get_db),
):
    """Create a new empirical claim with explicit type categorization."""
    repo = EvidenceRepository(db)
    claim = await repo.create_claim(
        text=payload.text,
        claim_type=payload.claim_type,
        confidence=payload.confidence,
        packet_id=payload.packet_id,
        is_verified=payload.is_verified,
    )
    return {
        "id": claim.id,
        "packet_id": claim.packet_id,
        "text": claim.text,
        "claim_type": claim.claim_type,
        "confidence": claim.confidence,
        "is_verified": claim.is_verified,
        "created_at": claim.created_at.isoformat(),
    }


@router.get("/claims")
async def list_claims(
    packet_id: Optional[str] = Query(None),
    claim_type: Optional[str] = Query(None),
    is_verified: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List tracked claims with verification status."""
    repo = EvidenceRepository(db)
    claims = await repo.list_claims(
        packet_id=packet_id,
        claim_type=claim_type,
        is_verified=is_verified,
        limit=limit,
    )
    return [
        {
            "id": c.id,
            "packet_id": c.packet_id,
            "text": c.text,
            "claim_type": c.claim_type,
            "confidence": c.confidence,
            "is_verified": c.is_verified,
            "evidence_count": len(c.evidence_links),
            "created_at": c.created_at.isoformat(),
        }
        for c in claims
    ]


@router.get("/claims/{claim_id}")
async def get_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get single claim with detailed evidence links and usages."""
    repo = EvidenceRepository(db)
    claim = await repo.get_claim_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")

    return {
        "id": claim.id,
        "packet_id": claim.packet_id,
        "text": claim.text,
        "claim_type": claim.claim_type,
        "confidence": claim.confidence,
        "is_verified": claim.is_verified,
        "evidence_links": [
            {
                "id": link.id,
                "quote": link.quote,
                "confidence": link.confidence,
                "source": {
                    "id": link.source.id,
                    "url": link.source.url,
                    "title": link.source.title,
                    "domain": link.source.domain,
                    "source_type": link.source.source_type,
                    "trust_weight": link.source.trust_weight,
                }
                if link.source
                else None,
            }
            for link in claim.evidence_links
        ],
        "created_at": claim.created_at.isoformat(),
    }


@router.get("/claims/{claim_id}/provenance", response_model=ProvenanceTrace)
async def get_claim_provenance(
    claim_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Traverse complete provenance graph for a claim."""
    repo = EvidenceRepository(db)
    trace = await repo.trace_provenance(claim_id)
    if "error" in trace:
        raise HTTPException(status_code=404, detail=trace["error"])
    return trace


@router.post("/claims/{claim_id}/link-source")
async def link_source_evidence(
    claim_id: str,
    payload: LinkEvidenceInput,
    db: AsyncSession = Depends(get_db),
):
    """Link citation source and quote to a claim, verifying it."""
    repo = EvidenceRepository(db)
    claim = await repo.get_claim_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")

    source_id = payload.source_id
    if not source_id and payload.source_url:
        existing_source = await repo.get_source_by_url(payload.source_url)
        if existing_source:
            source_id = existing_source.id
        else:
            from urllib.parse import urlparse
            domain = urlparse(payload.source_url).netloc or "external"
            new_source = await repo.create_source(
                url=payload.source_url,
                title=payload.source_title or payload.source_url,
                domain=domain,
                source_type=payload.source_type,
                trust_weight=payload.trust_weight,
            )
            source_id = new_source.id

    evidence = await repo.link_evidence(
        claim_id=claim_id,
        source_id=source_id,
        quote=payload.quote,
        confidence=payload.confidence,
        notes=payload.notes,
    )
    return {
        "id": evidence.id,
        "claim_id": evidence.claim_id,
        "source_id": evidence.source_id,
        "quote": evidence.quote,
        "is_claim_verified": True,
    }


@router.post("/claims/{claim_id}/label-opinion")
async def label_claim_opinion(
    claim_id: str,
    payload: LabelOpinionInput,
    db: AsyncSession = Depends(get_db),
):
    """Classify an assertion as opinion or prediction rather than empirical fact."""
    repo = EvidenceRepository(db)
    claim = await repo.label_opinion(claim_id, as_type=payload.claim_type)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")
    return {
        "id": claim.id,
        "claim_type": claim.claim_type,
        "message": f"Claim labeled as {payload.claim_type}.",
    }


# ---------------------------------------------------------
# Experiments & Measurements
# ---------------------------------------------------------
@router.post("/experiments", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: CreateExperimentInput,
    db: AsyncSession = Depends(get_db),
):
    """Create a new original studio benchmark or test experiment."""
    repo = EvidenceRepository(db)
    exp = await repo.create_experiment(
        title=payload.title,
        hypothesis=payload.hypothesis,
        method=payload.method,
        opportunity_id=payload.opportunity_id,
        tools_models=payload.tools_models,
        parameters=payload.parameters,
    )
    return {
        "id": exp.id,
        "title": exp.title,
        "hypothesis": exp.hypothesis,
        "method": exp.method,
        "opportunity_id": exp.opportunity_id,
        "created_at": exp.created_at.isoformat(),
    }


@router.get("/experiments")
async def list_experiments(
    opportunity_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List original experiments and their runs."""
    repo = EvidenceRepository(db)
    experiments = await repo.list_experiments(opportunity_id=opportunity_id, limit=limit)
    return [
        {
            "id": e.id,
            "title": e.title,
            "hypothesis": e.hypothesis,
            "opportunity_id": e.opportunity_id,
            "run_count": len(e.runs),
            "conclusions_count": len(e.conclusions),
            "created_at": e.created_at.isoformat(),
        }
        for e in experiments
    ]


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get experiment details with measurements and conclusions."""
    repo = EvidenceRepository(db)
    exp = await repo.get_experiment_by_id(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found.")

    return {
        "id": exp.id,
        "title": exp.title,
        "hypothesis": exp.hypothesis,
        "method": exp.method,
        "tools_models": exp.tools_models,
        "parameters": exp.parameters,
        "runs": [
            {
                "id": r.id,
                "run_number": r.run_number,
                "execution_time_ms": r.execution_time_ms,
                "cost_usd": r.cost_usd,
                "status": r.status,
                "measurements": [
                    {
                        "id": m.id,
                        "metric": m.metric,
                        "value": m.value,
                        "unit": m.unit,
                        "context": m.context,
                    }
                    for m in r.measurements
                ],
            }
            for r in exp.runs
        ],
        "conclusions": [
            {
                "id": c.id,
                "summary": c.summary,
                "confidence": c.confidence,
                "claim_id": c.claim_id,
            }
            for c in exp.conclusions
        ],
        "created_at": exp.created_at.isoformat(),
    }


@router.post("/experiments/{experiment_id}/runs")
async def add_experiment_run(
    experiment_id: str,
    payload: AddRunInput,
    db: AsyncSession = Depends(get_db),
):
    """Record an empirical run with quantitative measurements."""
    repo = EvidenceRepository(db)
    exp = await repo.get_experiment_by_id(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found.")

    run = await repo.add_experiment_run(
        experiment_id=experiment_id,
        run_number=payload.run_number,
        execution_time_ms=payload.execution_time_ms,
        cost_usd=payload.cost_usd,
        status=payload.status,
        error_message=payload.error_message,
        measurements=payload.measurements,
    )
    return {
        "id": run.id,
        "experiment_id": run.experiment_id,
        "run_number": run.run_number,
        "measurement_count": len(payload.measurements),
        "status": run.status,
    }


@router.post("/experiments/{experiment_id}/conclusions")
async def add_conclusion(
    experiment_id: str,
    payload: AddConclusionInput,
    db: AsyncSession = Depends(get_db),
):
    """Synthesize empirical findings into a verified conclusion."""
    repo = EvidenceRepository(db)
    exp = await repo.get_experiment_by_id(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found.")

    conclusion = await repo.add_conclusion(
        experiment_id=experiment_id,
        summary=payload.summary,
        claim_id=payload.claim_id,
        confidence=payload.confidence,
    )
    return {
        "id": conclusion.id,
        "experiment_id": conclusion.experiment_id,
        "summary": conclusion.summary,
        "claim_id": conclusion.claim_id,
        "confidence": conclusion.confidence,
    }


# ---------------------------------------------------------
# Content Claims & Script Quality Gate
# ---------------------------------------------------------
@router.post("/content-claims")
async def map_claim_to_content(
    claim_id: str = Query(...),
    content_id: str = Query(...),
    quote_in_script: str = Query(...),
    section_id: str = Query("evidence"),
    db: AsyncSession = Depends(get_db),
):
    """Map a claim into a script section."""
    repo = EvidenceRepository(db)
    cc = await repo.create_content_claim(
        claim_id=claim_id,
        content_id=content_id,
        quote_in_script=quote_in_script,
        section_id=section_id,
    )
    return {
        "id": cc.id,
        "claim_id": cc.claim_id,
        "content_id": cc.content_id,
        "section_id": cc.section_id,
        "verification_status": cc.verification_status,
    }


@router.get("/content-claims/{content_id}")
async def list_content_claims(
    content_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all claims mapped into a script/content piece."""
    repo = EvidenceRepository(db)
    claims = await repo.list_content_claims(content_id)
    return [
        {
            "id": cc.id,
            "claim_id": cc.claim_id,
            "claim_text": cc.claim.text if cc.claim else "",
            "claim_type": cc.claim.claim_type if cc.claim else "external_fact",
            "section_id": cc.section_id,
            "quote_in_script": cc.quote_in_script,
            "verification_status": cc.verification_status,
            "is_overridden": cc.is_overridden,
            "override_reason": cc.override_reason,
        }
        for cc in claims
    ]


@router.post("/content-claims/{content_claim_id}/override")
async def override_content_claim(
    content_claim_id: str,
    payload: OverrideClaimInput,
    db: AsyncSession = Depends(get_db),
):
    """Explicit human creator override for an unsupported claim with mandatory reason."""
    repo = EvidenceRepository(db)
    cc = await repo.override_content_claim(content_claim_id, reason=payload.override_reason)
    if not cc:
        raise HTTPException(status_code=404, detail=f"Content claim {content_claim_id} not found.")
    return {
        "id": cc.id,
        "verification_status": cc.verification_status,
        "is_overridden": cc.is_overridden,
        "override_reason": cc.override_reason,
    }


@router.post("/coverage", response_model=CoverageReport)
async def get_evidence_coverage(
    packet_id: Optional[str] = Query(None),
    content_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Calculate evidence coverage percentages and quality gate evaluation."""
    repo = EvidenceRepository(db)
    return await repo.calculate_coverage(packet_id=packet_id, content_id=content_id)


# ---------------------------------------------------------
# Engine Execution
# ---------------------------------------------------------
@router.post("/run", response_model=EngineResult)
async def run_evidence_engine(
    payload: Optional[EvidenceEngineInput] = None,
    db: AsyncSession = Depends(get_db),
):
    """Execute Evidence Engine analysis on claims or research packet."""
    engine = engine_registry.get("evidence")
    if not engine:
        engine = EvidenceEngine()

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
async def dry_run_evidence_engine(
    payload: Optional[EvidenceEngineInput] = None,
    db: AsyncSession = Depends(get_db),
):
    """Dry run Evidence Engine analysis without persisting changes."""
    engine = engine_registry.get("evidence")
    if not engine:
        engine = EvidenceEngine()

    run_id = f"dry_run_{uuid.uuid4()}"
    params = payload.model_dump(mode="json") if payload else {}
    context = EngineContext(
        run_id=run_id,
        dry_run=True,
        trigger="manual",
        parameters=params,
    )
    return await engine.dry_run(context)
