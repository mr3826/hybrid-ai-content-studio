from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TopicSignal(BaseModel):
    """Normalized atomic signal from a source feed, manual entry, or external provider."""
    signal_id: str
    source_type: str = "rss"  # "rss", "manual", "reddit", "hackernews", "github", "youtube"
    source_name: str
    title: str
    url: Optional[str] = None
    summary: str = ""
    published_at: datetime
    entities: List[str] = Field(default_factory=list)
    pillar: Optional[str] = None
    trust_weight: float = Field(default=0.8, ge=0.0, le=1.0)
    is_in_niche: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrendScoreBreakdown(BaseModel):
    """Detailed score decomposition for explainability and tuning."""
    base_mentions_score: float = Field(..., description="Score contribution from total mention count (0-100)")
    source_diversity_score: float = Field(..., description="Score contribution from distinct sources/domains (0-100)")
    source_authority_score: float = Field(..., description="Score contribution from source trust weights (0-100)")
    recency_score: float = Field(..., description="Decaying score based on first-seen timestamp (0-100)")
    velocity_score: float = Field(..., description="Score contribution from mentions per hour acceleration (0-100)")
    baseline_ratio: float = Field(..., description="Velocity compared to historical baseline e.g. 1.8 for +180%")
    manual_boost: float = Field(default=1.0, description="User applied boost multiplier")
    is_suppressed: bool = Field(default=False, description="Whether topic has been manually suppressed")
    raw_score: float = Field(..., description="Unadjusted weighted sum")
    final_score: float = Field(..., description="Boost-adjusted and clamped score (0-100)")


class TrendExplanation(BaseModel):
    """Human-readable explainability for a trend momentum score."""
    topic_key: str
    title: str
    summary: str  # e.g. "6 independent mentions across 4 trusted sources; first seen 42m ago; +180% vs baseline"
    mentions_text: str  # "6 independent mentions"
    sources_text: str  # "4 trusted sources"
    recency_text: str  # "first seen 42m ago"
    baseline_text: str  # "+180% vs baseline"
    velocity_text: str  # "2.8 mentions/hr"
    breakdown: TrendScoreBreakdown


class TrendCluster(BaseModel):
    """Topic cluster aggregating signals with momentum, authority, and velocity scoring."""
    topic_key: str
    title: str
    summary: str
    pillar: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    signals: List[TopicSignal] = Field(default_factory=list)
    first_seen_at: datetime
    last_seen_at: datetime
    mention_count: int
    distinct_sources_count: int
    velocity: float  # mentions per hour
    velocity_ratio: float  # relative change vs baseline
    source_diversity_score: float  # 0.0 - 1.0
    source_authority_score: float  # 0.0 - 1.0
    trend_score: float  # 0.0 - 100.0
    momentum_score: float  # 0.0 - 100.0
    manual_boost: float = 1.0
    is_suppressed: bool = False
    status: str = "active"  # "emerging", "active", "cooling", "archived"
    explanation: TrendExplanation


class TrendEngineInput(BaseModel):
    """Input payload to trigger a Trends Engine analysis run."""
    include_rss: bool = True
    include_manual: bool = True
    time_window_hours: int = 72
    min_mentions: int = 1
    custom_signals: List[TopicSignal] = Field(default_factory=list)


class TrendEngineResult(BaseModel):
    """Engine run execution summary."""
    clusters_analyzed: int
    active_trends: List[TrendCluster]
    emerging_count: int
    suppressed_count: int
    average_velocity: float = 0.0
