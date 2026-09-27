from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContentFormat(str, Enum):
    SHORT_VERTICAL = "short_vertical"
    YOUTUBE_LONG = "youtube_long"
    SOCIAL_POST = "social_post"
    NEWSLETTER = "newsletter"
    ARTICLE = "article"


class PlatformTarget(str, Enum):
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    CROSS_PLATFORM = "cross_platform"
    NONE = "none"


class HookType(str, Enum):
    CURIOSITY_GAP = "curiosity_gap"
    BOLD_CLAIM = "bold_claim"
    PROBLEM_AGITATION = "problem_agitation"
    SURPRISING_STAT = "surprising_stat"
    STORY_OPEN = "story_open"
    DIRECT_VALUE = "direct_value"


class ContentFamilyCreateInput(BaseModel):
    title: str = Field(..., description="High-level title for the Content Family investment")
    content_pillar: str = Field(default="Core", description="Parent content pillar")
    original_value_type: str = Field(default="benchmark", description="Originality format")
    summary: str = Field(default="", description="Executive summary of the empirical finding")
    topic_id: Optional[str] = Field(None, description="Optional opportunity ID")
    research_packet_id: Optional[str] = Field(None, description="Linked Research Packet ID")
    originality_plan_id: Optional[str] = Field(None, description="Linked Originality Plan ID")
    primary_experiment_id: Optional[str] = Field(None, description="Linked Experiment ID")
    research_cost: float = Field(default=0.0, description="Shared research cost in USD")
    experiment_cost: float = Field(default=0.0, description="Shared experiment cost in USD")
    ai_cost: float = Field(default=0.0, description="Shared AI cost in USD")
    media_cost: float = Field(default=0.0, description="Shared media cost in USD")
    manual_time_minutes: int = Field(default=0, description="Shared manual research time in minutes")
    local_compute_seconds: float = Field(default=0.0, description="Shared local hardware compute duration")

    model_config = ConfigDict(extra="ignore")


class ContentFamilyUpdateInput(BaseModel):
    title: Optional[str] = None
    content_pillar: Optional[str] = None
    original_value_type: Optional[str] = None
    summary: Optional[str] = None
    topic_id: Optional[str] = None
    research_packet_id: Optional[str] = None
    originality_plan_id: Optional[str] = None
    primary_experiment_id: Optional[str] = None
    status: Optional[str] = None
    research_cost: Optional[float] = None
    experiment_cost: Optional[float] = None
    ai_cost: Optional[float] = None
    media_cost: Optional[float] = None
    manual_time_minutes: Optional[int] = None
    local_compute_seconds: Optional[float] = None

    model_config = ConfigDict(extra="ignore")


class ContentItemCreateInput(BaseModel):
    format: str = Field(..., description="short_vertical, youtube_long, social_post, newsletter, article")
    working_title: str = Field(..., description="Working title for this specific asset")
    angle: str = Field(..., description="Child-specific angle distinct from other family items")
    platform_target: str = Field(default="youtube", description="Target publishing destination")
    hook_type: str = Field(default="bold_claim", description="Hook category")
    status: str = Field(default="PLANNED", description="Initial status")
    incremental_cost: float = Field(default=0.0, description="Child-specific incremental cost in USD")
    manual_time_minutes: int = Field(default=0, description="Child-specific editing time in minutes")
    local_compute_seconds: float = Field(default=0.0, description="Child-specific compute duration")
    original_value_connection: str = Field(default="", description="Explicit explanation of how child reflects originality")
    viewer_value: str = Field(default="", description="Viewer key takeaway")
    claim_ids: List[str] = Field(default_factory=list, description="Claim IDs selected from parent family")

    model_config = ConfigDict(extra="ignore")


class ContentItemUpdateInput(BaseModel):
    working_title: Optional[str] = None
    angle: Optional[str] = None
    hook_type: Optional[str] = None
    platform_target: Optional[str] = None
    format: Optional[str] = None
    status: Optional[str] = None
    incremental_cost: Optional[float] = None
    manual_time_minutes: Optional[int] = None
    local_compute_seconds: Optional[float] = None
    original_value_connection: Optional[str] = None
    viewer_value: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ChildItemProposal(BaseModel):
    format: str
    platform_target: str
    working_title: str
    angle: str
    hook_type: str
    evidence_focus: List[str] = Field(default_factory=list)
    original_value_connection: str = Field(default="")
    viewer_value: str = Field(default="")

    model_config = ConfigDict(extra="ignore")


class SuggestChildrenOutput(BaseModel):
    family_title: str
    proposals: List[ChildItemProposal]
    brand_applied: str
    pillar_applied: str

    model_config = ConfigDict(extra="ignore")


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class EconomicsSummary(BaseModel):
    shared_family_cost: float
    shared_manual_time_minutes: int
    shared_compute_seconds: float
    total_incremental_cost: float
    total_family_cost: float
    cost_per_child: float
    total_time_minutes: int
    total_compute_seconds: float
    roi_ratio: float = 0.0

    model_config = ConfigDict(extra="ignore")
