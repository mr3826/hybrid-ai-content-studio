from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.base import EngineContext
from app.engines.core.registry import engine_registry
from app.engines.analytics.analyzer import AnalyticsAnalyzer
from app.engines.analytics.contracts import (
    AnalyticsSummaryReport,
    CSVImportResponse,
    ContentROIAnalysis,
    HookPerformanceInsight,
    SnapshotCreateRequest,
    SnapshotResponse,
)
from app.repositories.analytics_repository import AnalyticsRepository


router = APIRouter(prefix="/analytics", tags=["Analytics"])


class CSVUploadPayload(BaseModel):
    csv_content: str


def _map_snapshot_to_response(s: Any, analyzer: AnalyticsAnalyzer) -> SnapshotResponse:
    engagement_rate = analyzer.calculate_engagement_rate(
        s.views, s.likes, s.comments, s.shares, s.saves
    )
    return SnapshotResponse(
        id=s.id,
        content_item_id=s.content_item_id,
        platform_publication_id=s.platform_publication_id,
        platform=s.platform,
        snapshot_timestamp=s.snapshot_timestamp,
        snapshot_label=s.snapshot_label,
        views=s.views,
        impressions=s.impressions,
        watch_time_seconds=s.watch_time_seconds,
        average_view_duration_seconds=s.average_view_duration_seconds,
        retention_rate_pct=s.retention_rate_pct,
        hook_retention_3s_pct=s.hook_retention_3s_pct,
        hook_retention_30s_pct=s.hook_retention_30s_pct,
        likes=s.likes,
        comments=s.comments,
        shares=s.shares,
        saves=s.saves,
        clicks=s.clicks,
        subscribers_gained=s.subscribers_gained,
        revenue_estimated_usd=s.revenue_estimated_usd,
        engagement_rate_pct=engagement_rate,
        notes=s.notes,
        source=s.source,
        raw_metadata=s.raw_metadata or {},
        created_at=s.created_at,
    )


@router.post(
    "/snapshots",
    response_model=SnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a manual publication metrics snapshot",
)
async def create_snapshot(
    payload: SnapshotCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> SnapshotResponse:
    repo = AnalyticsRepository(db)
    snapshot = await repo.record_snapshot(payload.model_dump())
    return _map_snapshot_to_response(snapshot, repo.analyzer)


@router.get(
    "/snapshots",
    response_model=List[SnapshotResponse],
    summary="List metrics snapshots with optional filtering",
)
async def list_snapshots(
    content_item_id: Optional[str] = Query(None, description="Filter by content item ID"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> List[SnapshotResponse]:
    repo = AnalyticsRepository(db)
    snapshots = await repo.list_snapshots(
        content_item_id=content_item_id,
        platform=platform,
        limit=limit,
    )
    return [_map_snapshot_to_response(s, repo.analyzer) for s in snapshots]


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
    summary="Get single snapshot details",
)
async def get_snapshot(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
) -> SnapshotResponse:
    repo = AnalyticsRepository(db)
    snapshot = await repo.get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot '{snapshot_id}' not found.",
        )
    return _map_snapshot_to_response(snapshot, repo.analyzer)


@router.delete(
    "/snapshots/{snapshot_id}",
    summary="Delete a metrics snapshot",
)
async def delete_snapshot(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AnalyticsRepository(db)
    deleted = await repo.delete_snapshot(snapshot_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot '{snapshot_id}' not found.",
        )
    return {"deleted": True, "id": snapshot_id}


@router.get(
    "/item/{content_item_id}",
    summary="Get comprehensive metrics history and ROI for a specific content item",
)
async def get_item_analytics(
    content_item_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AnalyticsRepository(db)
    snapshots = await repo.get_snapshots_by_item(content_item_id)
    roi = await repo.get_item_roi(content_item_id)

    total_views = sum(s.views for s in snapshots)
    total_likes = sum(s.likes for s in snapshots)
    total_comments = sum(s.comments for s in snapshots)
    total_shares = sum(s.shares for s in snapshots)
    total_saves = sum(s.saves for s in snapshots)
    total_revenue = sum(s.revenue_estimated_usd for s in snapshots)

    return {
        "content_item_id": content_item_id,
        "total_snapshots": len(snapshots),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_revenue_usd": round(total_revenue, 2),
        "engagement_rate_pct": repo.analyzer.calculate_engagement_rate(total_views, total_likes, total_comments, total_shares, total_saves),
        "roi_analysis": roi,
        "snapshots": [_map_snapshot_to_response(s, repo.analyzer) for s in snapshots],
    }


@router.get(
    "/summary",
    response_model=AnalyticsSummaryReport,
    summary="Get overall studio creator performance dashboard summary",
)
async def get_summary(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryReport:
    repo = AnalyticsRepository(db)
    summary_data = await repo.get_performance_summary(days=days)
    return AnalyticsSummaryReport(**summary_data)


@router.get(
    "/hooks",
    response_model=List[HookPerformanceInsight],
    summary="Get hook performance ranking and retention insights",
)
async def get_hook_rankings(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[HookPerformanceInsight]:
    repo = AnalyticsRepository(db)
    rankings = await repo.get_hook_rankings(limit=limit)
    return [HookPerformanceInsight(**r) for r in rankings]


@router.post(
    "/import-csv",
    response_model=CSVImportResponse,
    summary="Import publication metrics from CSV file content",
)
async def import_csv_metrics(
    payload: CSVUploadPayload,
    db: AsyncSession = Depends(get_db),
) -> CSVImportResponse:
    repo = AnalyticsRepository(db)
    records = repo.analyzer.parse_csv(payload.csv_content)

    imported_ids = []
    errors = []

    for idx, rec in enumerate(records):
        try:
            snapshot = await repo.record_snapshot(rec)
            imported_ids.append(snapshot.id)
        except Exception as e:
            errors.append(f"Row {idx + 1} failed: {str(e)}")

    return CSVImportResponse(
        imported_count=len(imported_ids),
        failed_count=len(errors),
        errors=errors,
        snapshot_ids=imported_ids,
    )


@router.post(
    "/run-engine",
    summary="Execute the Analytics Engine for batch analysis and audit logging",
)
async def run_analytics_engine(
    parameters: Optional[Dict[str, Any]] = Body(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    engine = engine_registry.get("analytics")
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics Engine not registered in engine catalog.",
        )

    # If no snapshots passed in params, fetch recent snapshots from repo
    params = parameters or {}
    if "snapshots" not in params:
        repo = AnalyticsRepository(db)
        raw_snapshots = await repo.list_snapshots(limit=50)
        params["snapshots"] = [
            {
                "content_item_id": s.content_item_id,
                "platform": s.platform,
                "views": s.views,
                "likes": s.likes,
                "comments": s.comments,
                "shares": s.shares,
                "saves": s.saves,
                "revenue_estimated_usd": s.revenue_estimated_usd,
                "retention_rate_pct": s.retention_rate_pct,
                "hook_retention_3s_pct": s.hook_retention_3s_pct,
                "hook_retention_30s_pct": s.hook_retention_30s_pct,
            }
            for s in raw_snapshots
        ]

    import uuid
    context = EngineContext(run_id=f"run-{uuid.uuid4().hex[:8]}", parameters=params)
    result = await engine.run(context, session=db)
    return result.model_dump()
