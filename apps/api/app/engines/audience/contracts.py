from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MagnetType(str, Enum):
    CHEAT_SHEET = "cheat_sheet"
    CHECKLIST = "checklist"
    TEMPLATE = "template"
    CODE_REPOSITORY = "code_repository"
    FREE_GUIDE = "free_guide"
    MINI_COURSE = "mini_course"
    TOOL = "tool"


class MagnetStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class LeadMagnetCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    magnet_type: MagnetType = MagnetType.CHEAT_SHEET
    landing_page_url: str = Field(..., min_length=5, max_length=512)
    cta_copy: str = Field(..., min_length=3)
    status: MagnetStatus = MagnetStatus.ACTIVE
    target_pillar: str = Field("Core", max_length=128)
    estimated_value_usd: float = Field(15.0, ge=0.0)


class LeadMagnetUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    magnet_type: Optional[MagnetType] = None
    landing_page_url: Optional[str] = Field(None, min_length=5, max_length=512)
    cta_copy: Optional[str] = None
    status: Optional[MagnetStatus] = None
    target_pillar: Optional[str] = None
    estimated_value_usd: Optional[float] = Field(None, ge=0.0)


class LeadMagnetResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    magnet_type: str
    landing_page_url: str
    cta_copy: str
    status: str
    target_pillar: str
    estimated_value_usd: float
    total_downloads: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Computed metrics
    conversions_count: int = 0
    total_clicks: int = 0
    total_signups: int = 0
    total_customers: int = 0
    total_revenue_usd: float = 0.0
    conversion_rate_pct: float = 0.0
    estimated_asset_value_usd: float = 0.0


class ConversionRecordRequest(BaseModel):
    lead_magnet_id: Optional[str] = None
    content_item_id: Optional[str] = None
    platform: str = Field(..., min_length=2, max_length=32)
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    conversion_timestamp: Optional[datetime] = None
    clicks: int = Field(0, ge=0)
    signups: int = Field(0, ge=0)
    customers: int = Field(0, ge=0)
    revenue_usd: float = Field(0.0, ge=0.0)
    notes: Optional[str] = None
    source: str = "MANUAL"


class ConversionResponse(BaseModel):
    id: str
    lead_magnet_id: Optional[str] = None
    lead_magnet_title: Optional[str] = None
    content_item_id: Optional[str] = None
    content_item_title: Optional[str] = None
    platform: str
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    conversion_timestamp: Optional[datetime] = None
    clicks: int
    signups: int
    customers: int
    revenue_usd: float
    notes: Optional[str] = None
    source: str
    conversion_rate_pct: float = 0.0
    created_at: Optional[datetime] = None


class UTMBuilderRequest(BaseModel):
    base_url: str = Field(..., min_length=5, max_length=512)
    platform: str = Field(..., min_length=2, max_length=32)
    lead_magnet_slug: Optional[str] = None
    content_slug: Optional[str] = None
    campaign_name: Optional[str] = None
    custom_medium: Optional[str] = None


class UTMBuilderResponse(BaseModel):
    tracking_url: str
    utm_source: str
    utm_medium: str
    utm_campaign: str
    utm_content: Optional[str] = None
    formatted_markdown_link: str
    copy_paste_cta: str


class AudienceSummaryResponse(BaseModel):
    total_lead_magnets: int
    active_magnets: int
    total_clicks: int
    total_signups: int
    total_customers: int
    total_revenue_usd: float
    overall_conversion_rate_pct: float
    estimated_total_list_value_usd: float
    by_magnet_type: Dict[str, int] = Field(default_factory=dict)
    by_platform: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    top_performing_magnets: List[Dict[str, Any]] = Field(default_factory=list)


class AudienceExplainResponse(BaseModel):
    result_id: str
    summary: str
    factors: List[Dict[str, Any]]
    economics_breakdown: Dict[str, Any]
