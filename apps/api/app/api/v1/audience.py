import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.registry import engine_registry
from app.engines.audience.analyzer import AudienceAnalyzer
from app.engines.audience.contracts import (
    AudienceExplainResponse,
    AudienceSummaryResponse,
    ConversionRecordRequest,
    ConversionResponse,
    LeadMagnetCreateRequest,
    LeadMagnetResponse,
    LeadMagnetUpdateRequest,
    UTMBuilderRequest,
    UTMBuilderResponse,
)
from app.models.audience import LeadMagnet, AudienceConversion
from app.repositories.audience_repository import AudienceRepository

router = APIRouter(prefix="/audience", tags=["Audience"])


def _map_magnet_to_response(magnet: LeadMagnet, metrics: Optional[Dict[str, Any]] = None) -> LeadMagnetResponse:
    metrics = metrics or {}
    total_signups = metrics.get("total_signups", magnet.total_downloads)
    est_val = round(total_signups * magnet.estimated_value_usd, 2)
    return LeadMagnetResponse(
        id=magnet.id,
        title=magnet.title,
        slug=magnet.slug,
        description=magnet.description,
        magnet_type=magnet.magnet_type,
        landing_page_url=magnet.landing_page_url,
        cta_copy=magnet.cta_copy,
        status=magnet.status,
        target_pillar=magnet.target_pillar,
        estimated_value_usd=magnet.estimated_value_usd,
        total_downloads=magnet.total_downloads,
        created_at=magnet.created_at,
        updated_at=magnet.updated_at,
        conversions_count=metrics.get("conversions_count", 0),
        total_clicks=metrics.get("total_clicks", 0),
        total_signups=total_signups,
        total_customers=metrics.get("total_customers", 0),
        total_revenue_usd=metrics.get("total_revenue_usd", 0.0),
        conversion_rate_pct=metrics.get("conversion_rate_pct", 0.0),
        estimated_asset_value_usd=est_val,
    )


def _map_conversion_to_response(conv: AudienceConversion) -> ConversionResponse:
    conv_rate = round((conv.signups / conv.clicks * 100), 2) if conv.clicks > 0 else 0.0
    return ConversionResponse(
        id=conv.id,
        lead_magnet_id=conv.lead_magnet_id,
        lead_magnet_title=conv.lead_magnet.title if conv.lead_magnet else None,
        content_item_id=conv.content_item_id,
        content_item_title=conv.content_item.working_title if conv.content_item else None,
        platform=conv.platform,
        utm_source=conv.utm_source,
        utm_medium=conv.utm_medium,
        utm_campaign=conv.utm_campaign,
        conversion_timestamp=conv.conversion_timestamp,
        clicks=conv.clicks,
        signups=conv.signups,
        customers=conv.customers,
        revenue_usd=conv.revenue_usd,
        notes=conv.notes,
        source=conv.source,
        conversion_rate_pct=conv_rate,
        created_at=conv.created_at,
    )


@router.get("/summary", response_model=AudienceSummaryResponse)
async def get_audience_summary(
    db: AsyncSession = Depends(get_db),
):
    """Returns aggregated executive summary of owned audience assets, economics, and conversion rates."""
    repo = AudienceRepository(db)
    summary = await repo.get_audience_summary()
    return AudienceSummaryResponse(**summary)


@router.get("/magnets", response_model=List[LeadMagnetResponse])
async def list_lead_magnets(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, PAUSED, ARCHIVED)"),
    magnet_type: Optional[str] = Query(None, description="Filter by magnet type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List lead magnets with computed conversion analytics."""
    repo = AudienceRepository(db)
    magnets = await repo.list_lead_magnets(status=status, magnet_type=magnet_type, limit=limit, offset=offset)
    
    results = []
    for m in magnets:
        metrics = await repo.get_magnet_metrics(m.id)
        results.append(_map_magnet_to_response(m, metrics))
    return results


@router.get("/magnets/{magnet_id}", response_model=LeadMagnetResponse)
async def get_lead_magnet(
    magnet_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch single lead magnet details."""
    repo = AudienceRepository(db)
    magnet = await repo.get_lead_magnet(magnet_id)
    if not magnet:
        raise HTTPException(status_code=404, detail="Lead magnet not found")
    metrics = await repo.get_magnet_metrics(magnet.id)
    return _map_magnet_to_response(magnet, metrics)


@router.post("/magnets", response_model=LeadMagnetResponse, status_code=status.HTTP_201_CREATED)
async def create_lead_magnet(
    payload: LeadMagnetCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new lead magnet asset."""
    repo = AudienceRepository(db)
    existing = await repo.get_lead_magnet_by_slug(payload.slug)
    if existing:
        raise HTTPException(status_code=400, detail=f"Lead magnet with slug '{payload.slug}' already exists")
    magnet = await repo.create_lead_magnet(payload.model_dump())
    return _map_magnet_to_response(magnet)


@router.put("/magnets/{magnet_id}", response_model=LeadMagnetResponse)
async def update_lead_magnet(
    magnet_id: str,
    payload: LeadMagnetUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update lead magnet settings."""
    repo = AudienceRepository(db)
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "slug" in update_data:
        existing = await repo.get_lead_magnet_by_slug(update_data["slug"])
        if existing and existing.id != magnet_id:
            raise HTTPException(status_code=400, detail=f"Slug '{update_data['slug']}' is already in use")

    updated = await repo.update_lead_magnet(magnet_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Lead magnet not found")
    metrics = await repo.get_magnet_metrics(updated.id)
    return _map_magnet_to_response(updated, metrics)


@router.delete("/magnets/{magnet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead_magnet(
    magnet_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a lead magnet."""
    repo = AudienceRepository(db)
    success = await repo.delete_lead_magnet(magnet_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead magnet not found")
    return None


@router.get("/conversions", response_model=List[ConversionResponse])
async def list_conversions(
    lead_magnet_id: Optional[str] = Query(None, description="Filter by lead magnet ID"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    content_item_id: Optional[str] = Query(None, description="Filter by content item ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List conversion records with attribution metadata."""
    repo = AudienceRepository(db)
    conversions = await repo.list_conversions(
        lead_magnet_id=lead_magnet_id,
        platform=platform,
        content_item_id=content_item_id,
        limit=limit,
        offset=offset,
    )
    return [_map_conversion_to_response(c) for c in conversions]


@router.post("/conversions", response_model=ConversionResponse, status_code=status.HTTP_201_CREATED)
async def record_conversion(
    payload: ConversionRecordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a conversion event or traffic snapshot."""
    repo = AudienceRepository(db)
    conv = await repo.record_conversion(payload.model_dump())
    loaded = await repo.get_conversion(conv.id)
    return _map_conversion_to_response(loaded or conv)


@router.post("/build-utm", response_model=UTMBuilderResponse)
async def build_utm(
    payload: UTMBuilderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate tracked UTM URL and ready-to-paste markdown CTA snippets."""
    magnet_title = None
    cta_copy = None
    if payload.lead_magnet_slug:
        repo = AudienceRepository(db)
        magnet = await repo.get_lead_magnet_by_slug(payload.lead_magnet_slug)
        if magnet:
            magnet_title = magnet.title
            cta_copy = magnet.cta_copy

    engine = engine_registry.get("audience")
    rules = engine.rules if engine else {}
    analyzer = AudienceAnalyzer(rules=rules)
    return analyzer.build_utm_tracking_url(
        request=payload,
        magnet_title=magnet_title,
        cta_copy=cta_copy,
    )


@router.get("/explain", response_model=AudienceExplainResponse)
async def explain_audience_economics(
    db: AsyncSession = Depends(get_db),
):
    """Explains subscriber valuation methodology, benchmarks, and UTM attribution taxonomy."""
    engine = engine_registry.get("audience")
    if not engine:
        raise HTTPException(status_code=500, detail="Audience engine not registered")
    
    explanation = engine.explain("audience-economics-v1")
    target_rate = engine.rules.get("target_conversion_rate_pct", 3.0)
    lead_val = engine.rules.get("default_lead_value_usd", 15.0)

    return AudienceExplainResponse(
        result_id=explanation.result_id,
        summary=explanation.summary,
        factors=explanation.factors,
        economics_breakdown={
            "target_conversion_rate_pct": target_rate,
            "default_lead_value_usd": lead_val,
            "formula": "Estimated Asset Value = Active Signups × Lead Valuation USD",
            "attribution_rule": "Deterministic Last-Touch with content item provenance via UTM parameter matrix",
        },
    )
