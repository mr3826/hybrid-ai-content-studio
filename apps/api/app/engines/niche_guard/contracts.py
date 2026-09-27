from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NicheGuardInput(BaseModel):
    """Input payload to evaluate against the single niche profile."""
    id: Optional[str] = Field(default=None, description="Candidate or content item identifier")
    title: str = Field(..., description="Headline or title to evaluate")
    text: str = Field(default="", description="Body text, summary, script, or description")
    tags: List[str] = Field(default_factory=list, description="Source tags or categorized keywords")
    url: Optional[str] = Field(default=None, description="Original source link or reference URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary context metadata")


class NicheGuardFactor(BaseModel):
    """Component factor contributing to niche relevance or rejection."""
    criterion: str = Field(..., description="Name of rule or criterion e.g. blocked_topics, pillar_match")
    points: float = Field(..., description="Points added or deducted")
    detail: str = Field(..., description="Human-readable explanation of this factor")
    matched_items: List[str] = Field(default_factory=list, description="Matched strings or tokens")


class NicheGuardVerdict(BaseModel):
    """Deterministic evaluation verdict produced by Niche Guard Engine."""
    id: str = Field(..., description="Unique verdict execution ID")
    input_id: Optional[str] = Field(default=None, description="ID of the evaluated item if provided")
    passed: bool = Field(..., description="True if content meets pass cutoff and has 0 blocked topics")
    score: float = Field(..., ge=0.0, le=100.0, description="Overall niche relevance score [0.0 - 100.0]")
    reason: str = Field(..., description="Summary explanation of the verdict")
    pillar_matches: List[str] = Field(default_factory=list, description="Matched content pillar names or IDs")
    matched_allowed_topics: List[str] = Field(default_factory=list, description="Matched allowed topics")
    matched_adjacent_topics: List[str] = Field(default_factory=list, description="Matched adjacent topics")
    matched_must_have_signals: List[str] = Field(default_factory=list, description="Matched must-have signals")
    matched_negative_keywords: List[str] = Field(default_factory=list, description="Matched negative keywords")
    blocked_topics_detected: List[str] = Field(default_factory=list, description="Blocked topics triggering hard block")
    factors: List[NicheGuardFactor] = Field(default_factory=list, description="Score component breakdown")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
