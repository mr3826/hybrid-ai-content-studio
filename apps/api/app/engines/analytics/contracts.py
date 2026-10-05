from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SnapshotCreateRequest(BaseModel):
    content_item_id: str
    platform: str
    snapshot_timestamp: Optional[datetime] = None
    snapshot_label: str = "24h"
    platform_publication_id: Optional[str] = None
    views: int = 0
    impressions: int = 0
    watch_time_seconds: float = 0.0
    average_view_duration_seconds: float = 0.0
    retention_rate_pct: float = 0.0
    hook_retention_3s_pct: Optional[float] = None
    hook_retention_30s_pct: Optional[float] = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    subscribers_gained: int = 0
    revenue_estimated_usd: float = 0.0
    notes: Optional[str] = None
    source: str = "MANUAL"
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class SnapshotResponse(BaseModel):
    id: str
    content_item_id: str
    platform_publication_id: Optional[str] = None
    platform: str
    snapshot_timestamp: datetime
    snapshot_label: str
    views: int
    impressions: int
    watch_time_seconds: float
    average_view_duration_seconds: float
    retention_rate_pct: float
    hook_retention_3s_pct: Optional[float] = None
    hook_retention_30s_pct: Optional[float] = None
    likes: int
    comments: int
    shares: int
    saves: int
    clicks: int
    subscribers_gained: int
    revenue_estimated_usd: float
    engagement_rate_pct: float = 0.0
    notes: Optional[str] = None
    source: str = "MANUAL"
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class HookPerformanceInsight(BaseModel):
    content_item_id: str
    content_title: str
    hook_text: str
    platform: str
    views: int
    hook_retention_3s_pct: float
    hook_retention_30s_pct: Optional[float] = None
    verdict: str
    recommendation: str


class PlatformBreakdown(BaseModel):
    platform: str
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_revenue: float
    avg_engagement_rate: float
    avg_retention_rate: float


class ContentROIAnalysis(BaseModel):
    content_item_id: str
    content_title: str
    ai_cost_usd: float
    creator_time_minutes: float
    creator_cost_usd: float
    total_cost_usd: float
    total_revenue_usd: float
    total_views: int
    net_profit_usd: float
    roi_multiplier: float
    revenue_per_1k_views_rpm: float
    status: str


class AnalyticsSummaryReport(BaseModel):
    days: int = 30
    total_snapshots: int
    total_published_items: int
    total_views: int
    total_impressions: int
    total_watch_time_hours: float
    total_engagements: int
    overall_engagement_rate_pct: float
    avg_3s_hook_retention_pct: float
    total_revenue_usd: float
    total_production_cost_usd: float
    overall_roi_multiplier: float
    platforms: List[PlatformBreakdown]
    top_hooks: List[HookPerformanceInsight]
    recent_snapshots: List[SnapshotResponse]


class CSVImportResponse(BaseModel):
    imported_count: int
    failed_count: int
    errors: List[str]
    snapshot_ids: List[str]
