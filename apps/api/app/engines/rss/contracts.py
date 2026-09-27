from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceFeedInput(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    category: str = "General"
    trust_weight: float = Field(default=0.8, ge=0.1, le=1.0)
    enabled: bool = True


class ParsedFeedItem(BaseModel):
    title: str
    link: str
    summary: str = ""
    published_at: datetime
    guid: Optional[str] = None
    feed_id: Optional[str] = None
    feed_name: str
    trust_weight: float = 0.8
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class CandidateSourceInfo(BaseModel):
    feed_id: Optional[str] = None
    feed_name: str
    url: str
    trust_weight: float
    published_at: str


class DiscoveryCandidate(BaseModel):
    id: str
    canonical_url: str
    title: str
    normalized_title: str
    summary: str = ""
    content_fingerprint: str
    primary_source: str
    published_at: datetime
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_count: int = 1
    sources: List[CandidateSourceInfo] = Field(default_factory=list)
    authority_score: float = 0.8
    pillar: Optional[str] = None
    niche_score: float = 0.0
    is_in_niche: bool = False
    niche_verdict: Dict[str, Any] = Field(default_factory=dict)
    status: str = "candidate"  # "candidate", "rejected", "promoted_to_opportunity"
    rejection_reason: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class RssFeedHealth(BaseModel):
    feed_id: str
    name: str
    url: str
    status: str  # "healthy", "failing", "disabled"
    last_success_at: Optional[str] = None
    last_failure_at: Optional[str] = None
    failure_count: int = 0
    last_error: Optional[str] = None


class RssEngineRunResult(BaseModel):
    feeds_polled: int = 0
    feeds_successful: int = 0
    feeds_failed: int = 0
    items_parsed: int = 0
    candidates_produced: int = 0
    rejected_old: int = 0
    rejected_off_niche: int = 0
    cross_source_grouped: int = 0
    candidates: List[DiscoveryCandidate] = Field(default_factory=list)
    feed_health: List[RssFeedHealth] = Field(default_factory=list)
    duration_ms: float = 0.0


class RssEngineExplainability(BaseModel):
    run_id: str
    engine_id: str = "rss"
    engine_version: str = "1.0.0"
    rules_version: str = "1.0.0"
    summary: str
    factors: Dict[str, Any] = Field(default_factory=dict)
    feed_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    grouping_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    niche_filter_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
