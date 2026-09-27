from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OpportunityScoreBreakdown(BaseModel):
    """Detailed score decomposition for all 10 editable dimensions."""
    niche_fit: float = Field(..., description="Niche alignment score (max 18)")
    original_value: float = Field(..., description="Original test/value potential (max 20)")
    audience_usefulness: float = Field(..., description="Audience usefulness score (max 15)")
    evergreen_value: float = Field(..., description="Search/evergreen value score (max 12)")
    trend_momentum: float = Field(..., description="Trend momentum score (max 10)")
    commercial_fit: float = Field(..., description="Commercial/affiliate fit score (max 10)")
    content_family_potential: float = Field(..., description="Multi-format potential (max 5)")
    sponsor_relevance: float = Field(..., description="Sponsor relevance score (max 3)")
    production_effort_score: float = Field(..., description="Effort economy score (max 4)")
    saturation_penalty: float = Field(default=0.0, description="Penalty for recent channel saturation")
    raw_score: float = Field(..., description="Unpenalized composite score")
    final_score: float = Field(..., description="Final opportunity score (0 - 100)")


class OpportunityItem(BaseModel):
    """Normalized content opportunity payload."""
    id: Optional[str] = None
    topic: str
    slug: str
    candidate_id: Optional[str] = None
    trend_id: Optional[str] = None
    pillar: Optional[str] = None
    status: str = "needs_review"  # "needs_review", "watching", "rejected", "approved", "research_ready", "in_production", "ready_to_publish", "published"
    opportunity_score: float
    trend_score: float
    originality_potential: float
    evergreen_value: float
    commercial_fit: float
    production_effort: str  # "low", "medium", "high"
    estimated_cost: float
    estimated_time_minutes: int
    suggested_original_angle: str
    suggested_content_family: str
    risks: List[str] = Field(default_factory=list)
    why: str
    recommended_action: str  # "Research", "Watch", "Reject"
    score_breakdown: OpportunityScoreBreakdown
    source_references: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class OpportunityEngineInput(BaseModel):
    """Input payload to trigger Opportunity intelligence scoring."""
    min_score: float = 30.0
    include_candidates: bool = True
    include_trends: bool = True
    limit: int = 50
    custom_topics: List[Dict[str, Any]] = Field(default_factory=list)


class OpportunityEngineResult(BaseModel):
    """Result summary of Opportunity Engine run."""
    analyzed_count: int
    created_count: int
    updated_count: int
    top_opportunities: List[OpportunityItem] = Field(default_factory=list)
    needs_review_count: int = 0
