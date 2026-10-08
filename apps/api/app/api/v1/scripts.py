import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, update
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.engines.ai.engine import AIProviderEngine
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
from app.models.evidence import Claim, Experiment, ExperimentRun
from app.models.script import ScriptDraft, ScriptSection
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.brand import BrandProfile, SINGLETON_BRAND_ID
from app.models.originality import OriginalityPlan
from app.models.opportunity import Opportunity
from app.models.research import ResearchPacket
from app.engines.core.registry import engine_registry
from app.repositories.content_family_repository import (
    ContentFamilyRepository,
    ContentItemRepository,
)
from app.repositories.script_repository import ScriptRepository
from app.services.script_generation import (
    ProjectBudgetExceeded,
    ScriptGenerationContext,
    ScriptGenerationError,
    ScriptGenerationService,
)

router = APIRouter(prefix="/scripts", tags=["Script Studio"])
engine = ContentEngine()
generation_service = ScriptGenerationService(engine)


def get_ai_provider_engine() -> AIProviderEngine:
    provider = engine_registry.get("ai")
    if isinstance(provider, AIProviderEngine):
        return provider
    return AIProviderEngine()


# Request / Response Schemas
class GenerateScriptPayload(BaseModel):
    content_item_id: str
    target_duration_sec: Optional[int] = Field(default=None, ge=15, le=900)
    guidance: Optional[str] = Field(default=None, max_length=2000)


class UpdateSectionPayload(BaseModel):
    heading: Optional[str] = Field(default=None, max_length=128)
    narration: Optional[str] = Field(default=None, max_length=8000)
    visual_cue: Optional[str] = Field(default=None, max_length=1200)
    linked_claim_ids: Optional[List[str]] = Field(default=None, max_length=50)


class RefineSectionPayload(BaseModel):
    refinement_type: RefinementType
    guidance: Optional[str] = Field(default=None, max_length=1200)


class ScriptSectionDetail(BaseModel):
    id: str
    section_type: str
    order_index: int
    heading: str
    narration: str
    visual_cue: str
    evidence_category: str = "context"
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
    generation_metadata: Optional[Dict[str, Any]] = None
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


APPROVED_TOPIC_STATES = {
    "approved",
    "research_ready",
    "in_production",
    "ready_to_publish",
    "published",
}


def _limited_text(value: Any, limit: int = 2400) -> str:
    return str(value or "")[:limit]


def _raise_generation_http_error(exc: ScriptGenerationError) -> None:
    message = str(exc)
    for secret in (settings.GEMINI_API_KEY, settings.QWEN_API_KEY):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    lower = message.casefold()
    if "budget would be exceeded" in lower or "budget exceeded" in lower:
        code = status.HTTP_429_TOO_MANY_REQUESTS
    elif any(
        marker in lower
        for marker in (
            "unsupported content format",
            "duration must be",
            "pacing allows",
            "exceeds the",
            "must contain between",
            "select at least one verified",
            "select verified evidence claims",
        )
    ):
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif "not configured" in lower or "api key" in lower or "no configured ai providers" in lower:
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        code = status.HTTP_502_BAD_GATEWAY
    raise HTTPException(status_code=code, detail=message) from exc


async def _load_script_generation_inputs(
    item: ContentItem,
    family: ContentFamily,
    db: AsyncSession,
    item_repo: ContentItemRepository,
    *,
    target_duration_sec: int,
    guidance: str,
) -> tuple[GenerateScriptRequest, ScriptGenerationContext]:
    if family.status not in {"READY_FOR_CONTENT", "ACTIVE", "COMPLETED"} or not family.approved_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve this content family before generating or refining its script.",
        )

    topic_snapshot: Optional[Dict[str, Any]] = None
    if family.topic_id:
        opportunity = await db.get(Opportunity, family.topic_id)
        if not opportunity or (opportunity.status or "").casefold() not in APPROVED_TOPIC_STATES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The linked topic has not passed the human topic approval gate.",
            )
        topic_snapshot = {"id": opportunity.id, "topic": opportunity.topic, "status": opportunity.status}

    packet = await db.get(ResearchPacket, family.research_packet_id) if family.research_packet_id else None
    if not packet or not packet.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verify the family research packet before generating or refining its script.",
        )

    plan = await db.get(OriginalityPlan, family.originality_plan_id) if family.originality_plan_id else None
    if (
        not plan
        or plan.status.casefold() != "approved"
        or plan.is_generic_summary
        or plan.packet_id not in (None, packet.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve a non-generic originality plan before generating or refining its script.",
        )

    selections = await item_repo.get_selected_claims(item.id)
    verified_selections = [
        selection
        for selection in selections
        if selection.claim
        and selection.claim.is_verified
        and selection.claim.packet_id in (None, packet.id)
    ]
    if not verified_selections:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select at least one verified claim from this research packet before script generation.",
        )

    warnings: list[str] = []
    if len(verified_selections) != len(selections):
        warnings.append("Unverified or unrelated selected claims were excluded from generation context.")

    claims_data: list[dict[str, Any]] = []
    numeric_parts: list[str] = []
    missing_source_count = 0
    for selection in verified_selections:
        claim: Claim = selection.claim
        provenance: list[dict[str, Any]] = []
        for evidence_link in claim.evidence_links or []:
            source = evidence_link.source
            if not source:
                continue
            published_at = source.published_at.isoformat() if source.published_at else None
            provenance.append(
                {
                    "source_id": source.id,
                    "title": _limited_text(source.title, 512),
                    "domain": _limited_text(source.domain, 255),
                    "url": _limited_text(source.url, 1024),
                    "source_type": _limited_text(source.source_type, 50),
                    "published_at": published_at,
                    "quote": _limited_text(evidence_link.quote, 900),
                    "page_or_timestamp": _limited_text(evidence_link.page_or_timestamp, 100),
                }
            )
        claim_text = _limited_text(claim.text, 4000)
        if claim.claim_type == "external_fact" and not provenance:
            missing_source_count += 1
        claims_data.append(
            {
                "id": claim.id,
                "text": claim_text,
                "claim_type": claim.claim_type,
                "is_verified": bool(claim.is_verified),
                "confidence": claim.confidence,
                "relevance_note": _limited_text(selection.relevance_note, 1200),
                "is_primary": bool(selection.is_primary),
                "provenance": provenance,
            }
        )
        numeric_parts.extend([claim_text, *(str(source.get("quote", "")) for source in provenance)])
        numeric_parts.extend(str(source.get("published_at") or "") for source in provenance)

    if missing_source_count:
        warnings.append(
            f"{missing_source_count} selected sourced fact(s) have no attached source record; review their provenance."
        )

    experiment_filters = [Experiment.originality_plan_id == plan.id]
    if family.primary_experiment_id:
        experiment_filters.append(Experiment.id == family.primary_experiment_id)
    experiment_query = (
        select(Experiment)
        .where(or_(*experiment_filters))
        .options(
            selectinload(Experiment.runs).selectinload(ExperimentRun.measurements),
        )
        .order_by(Experiment.created_at)
    )
    experiment_result = await db.execute(experiment_query)
    experiments = list(experiment_result.scalars().unique().all())
    experiment_context: list[dict[str, Any]] = []
    experiment_ids: list[str] = []
    completed_results_count = 0
    for experiment in experiments:
        run_context = []
        for run in experiment.runs or []:
            measurements = [
                {
                    "metric": _limited_text(measurement.metric, 255),
                    "value": measurement.value,
                    "unit": _limited_text(measurement.unit, 50),
                    "sample_size": measurement.sample_size,
                    "context": _limited_text(measurement.context, 800),
                }
                for measurement in (run.measurements or [])[:40]
            ]
            run_context.append(
                {
                    "run_number": run.run_number,
                    "status": run.status,
                    "execution_time_ms": run.execution_time_ms,
                    "measurements": measurements,
                }
            )
        actual_result_recorded = bool(
            experiment.results
            or experiment.conclusion
            or any(run.get("measurements") for run in run_context)
        )
        if experiment.status == "completed" and actual_result_recorded:
            completed_results_count += 1
            experiment_ids.append(experiment.id)
        record = {
            "id": experiment.id,
            "title": _limited_text(experiment.title, 255),
            "status": experiment.status,
            "actual_result_recorded": actual_result_recorded,
            "hypothesis": _limited_text(experiment.hypothesis, 1200),
            "method": _limited_text(experiment.method, 1800),
            "results_json": json.dumps(experiment.results or {}, ensure_ascii=False)[:5000],
            "failures": [_limited_text(value, 800) for value in (experiment.failures or [])[:20]],
            "conclusion": _limited_text(experiment.conclusion, 1600),
            "runs": run_context[:20],
        }
        experiment_context.append(record)
        if actual_result_recorded:
            numeric_parts.extend(
                [record["results_json"], record["conclusion"], json.dumps(run_context, ensure_ascii=False)]
            )

    if not completed_results_count:
        warnings.append(
            "No completed experiment results are recorded. The script must not imply that a creator experiment was run."
        )

    brand = await db.get(BrandProfile, SINGLETON_BRAND_ID)
    niche = await db.get(NicheProfile, SINGLETON_NICHE_ID)
    if not brand:
        warnings.append("The default brand voice is being used because no Brand Profile is configured.")
    if not niche:
        warnings.append("No Niche Profile is configured; the default niche boundaries are empty.")

    request = GenerateScriptRequest(
        content_item_id=item.id,
        format=item.format,
        working_title=item.working_title,
        angle=item.angle,
        hook_type=item.hook_type,
        platform_target=item.platform_target,
        target_duration_sec=target_duration_sec,
        viewer_value=item.viewer_value,
        family_title=family.title,
        content_pillar=family.content_pillar,
        original_value_type=plan.originality_type or family.original_value_type,
        what_are_we_adding=plan.what_are_we_adding or item.original_value_connection,
        evidence_claims=claims_data,
        brand_tone=brand.tone if brand else ["Direct", "Empirical", "Technical"],
        banned_cliches=brand.banned_cliches if brand else [],
        voice_rules=brand.voice_rules if brand else [],
        cta_style=brand.cta_style if brand else "soft_value",
        niche_allowed_topics=niche.allowed_topics if niche else [],
        niche_blocked_topics=niche.blocked_topics if niche else [],
    )
    plan_context = {
        "id": plan.id,
        "status": plan.status,
        "originality_type": plan.originality_type,
        "what_are_we_adding": _limited_text(plan.what_are_we_adding, 2400),
        "why_it_matters": _limited_text(plan.why_it_matters, 1800),
        "suggested_experiments_are_plans_not_results": [
            _limited_text(entry, 800) for entry in (plan.suggested_experiments or [])[:15]
        ],
    }
    context = ScriptGenerationContext(
        content_item_id=item.id,
        research_packet_id=packet.id,
        research_packet_version=packet.version,
        originality_plan_id=plan.id,
        originality_plan=plan_context,
        experiment_ids=experiment_ids,
        experiments=experiment_context,
        warnings=warnings,
        numeric_evidence="\n".join(numeric_parts),
        input_snapshot={
            "request": request.model_dump(mode="json"),
            "approved_topic": topic_snapshot,
            "research_packet": {"id": packet.id, "version": packet.version},
            "originality_plan": plan_context,
            "experiments": experiment_context,
            "completed_experiment_ids": experiment_ids,
        },
    )
    return request, context


async def _add_family_ai_cost(db: AsyncSession, family_id: str, amount: float) -> None:
    if amount <= 0:
        return
    await db.execute(
        update(ContentFamily)
        .where(ContentFamily.id == family_id)
        .values(ai_cost=ContentFamily.ai_cost + amount, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()


@router.post("/generate", response_model=ScriptDetailResponse)
async def generate_script_draft(
    payload: GenerateScriptPayload,
    db: AsyncSession = Depends(get_db),
    provider_engine: AIProviderEngine = Depends(get_ai_provider_engine),
):
    """Generate a structured script through the configured AI Provider Engine."""
    item_repo = ContentItemRepository(db)
    script_repo = ScriptRepository(db)

    item = await item_repo.get_item(payload.content_item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ContentItem {payload.content_item_id} not found.",
        )

    family = item.family
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent ContentFamily not found.",
        )

    if item.format == "short_vertical":
        target_duration = payload.target_duration_sec or 60
    elif item.format == "youtube_long":
        target_duration = payload.target_duration_sec or 600
    else:
        target_duration = 0

    req, context = await _load_script_generation_inputs(
        item,
        family,
        db,
        item_repo,
        target_duration_sec=target_duration,
        guidance=(payload.guidance or "").strip(),
    )
    try:
        result = await generation_service.generate(
            req,
            (payload.guidance or "").strip(),
            context,
            provider_engine,
            project_id=family.id,
            project_spend_usd=family.ai_cost,
            session=db,
        )
    except ProjectBudgetExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ScriptGenerationError as exc:
        _raise_generation_http_error(exc)
    draft_output = result.draft

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
        generation_metadata=result.metadata,
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
            evidence_category=sec.evidence_category,
            estimated_seconds=sec.estimated_seconds,
            word_count=sec.word_count,
            linked_claim_ids=sec.linked_claim_ids,
        )

    # Save initial revision
    await script_repo.create_revision(
        script_id=script.id,
        trigger="initial_generation",
        notes=(
            f"Initial {result.metadata['generation_mode']} script generation by "
            f"{result.metadata['provider']}/{result.metadata['model']}"
        ),
    )

    # Update quality scores on script
    if draft_output.quality_verdict:
        await script_repo.update_quality_scores(
            script.id, draft_output.quality_verdict.model_dump()
        )

    await _add_family_ai_cost(db, family.id, float(result.metadata.get("estimated_cost_usd", 0.0)))

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

    sec = next((section for section in script.sections if section.id == section_id), None)
    if not sec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section {section_id} not found for script {script_id}.",
        )

    if payload.narration is not None and (script.generation_metadata or {}).get("generation_mode") == "live":
        proposed_total_words = script.total_word_count - sec.word_count + len(payload.narration.split())
        try:
            generation_service.validate_total_word_count(
                script.format, script.target_duration_sec, proposed_total_words
            )
        except ScriptGenerationError as exc:
            _raise_generation_http_error(exc)

    updates = {}
    if payload.heading is not None:
        updates["heading"] = payload.heading
    if payload.narration is not None:
        updates["narration"] = payload.narration
    if payload.visual_cue is not None:
        updates["visual_cue"] = payload.visual_cue
    if payload.linked_claim_ids is not None:
        item_repo = ContentItemRepository(db)
        item = await item_repo.get_item(script.content_item_id)
        if not item or not item.family:
            raise HTTPException(status_code=409, detail="Script content family is no longer available.")
        packet_id = item.family.research_packet_id
        selected = await item_repo.get_selected_claims(script.content_item_id)
        verified_claims = {
            selection.claim.id: {
                "id": selection.claim.id,
                "claim_type": selection.claim.claim_type,
                "text": selection.claim.text,
            }
            for selection in selected
            if selection.claim
            and selection.claim.is_verified
            and selection.claim.packet_id in (None, packet_id)
        }
        unknown_ids = [claim_id for claim_id in payload.linked_claim_ids if claim_id not in verified_claims]
        if unknown_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Section links must reference claims selected and verified for this content item.",
                    "unknown_claim_ids": unknown_ids,
                },
            )
        updates["linked_claim_ids"] = payload.linked_claim_ids
        updates["evidence_category"] = generation_service._evidence_category(
            payload.linked_claim_ids, verified_claims
        )

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
    provider_engine: AIProviderEngine = Depends(get_ai_provider_engine),
):
    """Refine a section through the configured AI Provider Engine."""
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

    item_repo = ContentItemRepository(db)
    item = await item_repo.get_item(script.content_item_id)
    if not item or not item.family:
        raise HTTPException(status_code=404, detail="Script content item or family not found.")
    current_metadata = script.generation_metadata or {}
    if current_metadata.get("generation_mode") != "live" and not settings.AI_MOCK_MODE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Regenerate this legacy or mock script with a live provider before refining it.",
        )

    target_duration = script.target_duration_sec if script.format in ("short_vertical", "youtube_long") else 0
    generation_request, context = await _load_script_generation_inputs(
        item,
        item.family,
        db,
        item_repo,
        target_duration_sec=target_duration,
        guidance=(payload.guidance or "").strip(),
    )
    if current_metadata.get("input_snapshot_sha256") != generation_service.input_snapshot_hash(context):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Research, evidence, brand, niche, originality, or experiment inputs changed after generation. Regenerate the script before refining it.",
        )
    claims_data = generation_request.evidence_claims
    refine_req = SectionRefineRequest(
        script_id=script_id,
        section_id=section_id,
        section_type=sec.section_type,
        content_format=script.format,
        target_duration_sec=script.target_duration_sec,
        current_narration=sec.narration,
        current_visual_cue=sec.visual_cue,
        current_linked_claim_ids=sec.linked_claim_ids or [],
        refinement_type=payload.refinement_type,
        guidance=payload.guidance,
        linked_claims=claims_data,
        brand_tone=generation_request.brand_tone,
        voice_rules=generation_request.voice_rules,
        banned_cliches=generation_request.banned_cliches,
        niche_blocked_topics=generation_request.niche_blocked_topics,
    )

    try:
        result, metadata = await generation_service.refine(
            refine_req,
            claims_data,
            context,
            (payload.guidance or "").strip(),
            provider_engine,
            project_id=item.family.id,
            project_spend_usd=item.family.ai_cost,
            session=db,
        )
    except ProjectBudgetExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ScriptGenerationError as exc:
        _raise_generation_http_error(exc)

    if metadata.get("generation_mode") == "live":
        proposed_total_words = script.total_word_count - sec.word_count + result.word_count
        try:
            generation_service.validate_total_word_count(
                script.format, script.target_duration_sec, proposed_total_words
            )
        except ScriptGenerationError as exc:
            _raise_generation_http_error(exc)

    previous_history = list(current_metadata.get("operation_history", []))
    current_operation = (metadata.get("operation_history") or [{}])[-1]
    metadata["operation_history"] = previous_history + [current_operation]
    metadata["prompt_tokens"] = sum(int(entry.get("prompt_tokens") or 0) for entry in metadata["operation_history"])
    metadata["completion_tokens"] = sum(int(entry.get("completion_tokens") or 0) for entry in metadata["operation_history"])
    metadata["total_tokens"] = sum(int(entry.get("total_tokens") or 0) for entry in metadata["operation_history"])
    metadata["estimated_cost_usd"] = round(
        sum(float(entry.get("estimated_cost_usd") or 0) for entry in metadata["operation_history"]), 6
    )
    metadata["fallback_used"] = any(bool(entry.get("fallback_used")) for entry in metadata["operation_history"])
    metadata["approval_eligible"] = bool(
        current_metadata.get("approval_eligible")
        and current_metadata.get("generation_mode") == "live"
        and metadata.get("approval_eligible")
    )
    if not metadata["approval_eligible"]:
        metadata["generation_mode"] = "mock"
    metadata["warnings"] = list(dict.fromkeys(
        list(current_metadata.get("warnings", [])) + list(metadata.get("warnings", []))
    ))

    # Update in DB
    await script_repo.update_section(
        section_id,
        narration=result.new_narration,
        visual_cue=result.new_visual_cue,
        word_count=result.word_count,
        estimated_seconds=result.estimated_seconds,
        linked_claim_ids=result.linked_claim_ids,
        evidence_category=generation_service._evidence_category(
            result.linked_claim_ids,
            {str(claim["id"]): claim for claim in claims_data if claim.get("id")},
        ),
    )
    await script_repo.update_generation_metadata(script_id, metadata)
    await _add_family_ai_cost(
        db, item.family.id, float(current_operation.get("estimated_cost_usd", 0.0))
    )

    # Record revision
    await script_repo.create_revision(
        script_id=script_id,
        trigger=payload.refinement_type.value,
        notes=(
            f"Refined section ({payload.refinement_type.value}) using "
            f"{metadata['provider']}/{metadata['model']} ({metadata['generation_mode']})."
        ),
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

    metadata = script.generation_metadata or {}
    if metadata.get("generation_mode") != "live" or not metadata.get("approval_eligible"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Mock and legacy-unverified scripts cannot be approved. Generate the script with Gemini or Qwen first.",
                "blocking_reasons": ["missing_live_provider_provenance"],
            },
        )

    item_repo = ContentItemRepository(db)
    item = await item_repo.get_item(script.content_item_id)
    if not item or not item.family:
        raise HTTPException(status_code=409, detail="Script content family is no longer available.")
    family = item.family
    packet = await db.get(ResearchPacket, family.research_packet_id) if family.research_packet_id else None
    if (
        not packet
        or not packet.is_verified
        or packet.id != metadata.get("research_packet_id")
        or packet.version != metadata.get("research_packet_version")
        or family.originality_plan_id != metadata.get("originality_plan_id")
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Research or originality inputs changed after generation. Regenerate the script before approval.",
        )
    target_duration = script.target_duration_sec if script.format in ("short_vertical", "youtube_long") else 0
    _, current_context = await _load_script_generation_inputs(
        item,
        family,
        db,
        item_repo,
        target_duration_sec=target_duration,
        guidance="",
    )
    current_hash = generation_service.input_snapshot_hash(current_context)
    if current_hash != metadata.get("input_snapshot_sha256"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Research, evidence, brand, niche, originality, or experiment inputs changed after generation. "
                "Regenerate the script before approval."
            ),
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
    claims_data = [
        {"id": selection.claim.id, "text": selection.claim.text}
        for selection in claims
        if selection.claim
        and selection.claim.is_verified
        and selection.claim.packet_id in (None, family.research_packet_id if family else None)
    ]

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
            evidence_category=s.evidence_category,
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
    selected_claim_ids = {claim["id"] for claim in claims_data}
    linked_claim_ids = {claim_id for section in sec_outputs for claim_id in section.linked_claim_ids}
    if linked_claim_ids - selected_claim_ids:
        verdict.is_approvable = False
        verdict.blocking_reasons.append("script_links_unverified_or_unselected_claims")
        verdict.summary = "The script references evidence that is no longer selected and verified. " + verdict.summary
    metadata = script.generation_metadata or {}
    if metadata.get("generation_mode") != "live" or not metadata.get("approval_eligible"):
        verdict.is_approvable = False
        reason = "mock_output_unverified" if metadata.get("generation_mode") == "mock" else "legacy_output_unverified"
        if reason not in verdict.blocking_reasons:
            verdict.blocking_reasons.append(reason)
        verdict.summary = "Only live-provider output can pass the script approval gate. " + verdict.summary
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
        generation_metadata=script.generation_metadata,
        sections=[
            ScriptSectionDetail(
                id=s.id,
                section_type=s.section_type,
                order_index=s.order_index,
                heading=s.heading,
                narration=s.narration,
                visual_cue=s.visual_cue,
                evidence_category=s.evidence_category,
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
