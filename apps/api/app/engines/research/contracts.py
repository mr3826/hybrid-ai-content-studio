from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


ClaimStatus = Literal["source-backed", "explicitly_uncertain", "manually_entered"]


class SourceReference(BaseModel):
    """Traceable citation link with publication metadata."""
    url: str = Field(..., description="Canonical source URL")
    title: str = Field(..., description="Document or article headline")
    domain: str = Field(..., description="Source origin hostname")
    excerpt: str = Field(default="", description="Relevant contextual quote or excerpt")
    trust_weight: float = Field(default=1.0, description="Source credibility weight (0.0 to 1.5)")
    published_at: Optional[str] = Field(default=None, description="ISO timestamp if available")


class FactItem(BaseModel):
    """Verified factual statement extracted with direct citation."""
    id: str
    text: str
    source_url: str
    source_title: Optional[str] = None
    confidence: float = Field(default=0.95, description="Confidence score 0.0 - 1.0")


class NumberMetric(BaseModel):
    """Measurable quantitative data point or benchmark."""
    id: str
    metric: str
    value: str
    unit: Optional[str] = None
    context: str = ""
    source_url: str


class DateItem(BaseModel):
    """Chronological milestone, release date, or deadline."""
    id: str
    event: str
    date_str: str
    source_url: str


class EntityItem(BaseModel):
    """Named framework, tool, organization, or model identified."""
    id: str
    name: str
    type: str = "Technology"
    relevance: float = 1.0
    source_url: Optional[str] = None


class ClaimItem(BaseModel):
    """Factual claim with strict verification status categorization.
    Must be: source-backed, explicitly_uncertain, or manually_entered.
    """
    id: str
    claim_text: str
    verification_status: ClaimStatus
    evidence_quote: Optional[str] = None
    source_url: Optional[str] = None
    uncertainty_reason: Optional[str] = None
    confidence: float = 0.90


class ContradictionItem(BaseModel):
    """Direct conflict detected between two or more cited sources."""
    id: str
    claim_a: str
    source_a: str
    claim_b: str
    source_b: str
    conflict_summary: str


class UncertainClaimItem(BaseModel):
    """Claim flagged with explicit reasons why verification is incomplete."""
    id: str
    claim_text: str
    uncertainty_reason: str


class ThingNotToClaimItem(BaseModel):
    """Unverified vendor marketing hype or superlative to actively avoid in scripts."""
    id: str
    claim_text: str
    reason_to_avoid: str
    flagged_source: Optional[str] = None


class ResearchPacketItem(BaseModel):
    """Complete traceable research packet for downstream script synthesis."""
    id: str
    opportunity_id: Optional[str] = None
    topic: str
    slug: str
    summary: str
    primary_sources: List[SourceReference] = Field(default_factory=list)
    supporting_sources: List[SourceReference] = Field(default_factory=list)
    facts: List[FactItem] = Field(default_factory=list)
    numbers: List[NumberMetric] = Field(default_factory=list)
    dates: List[DateItem] = Field(default_factory=list)
    entities: List[EntityItem] = Field(default_factory=list)
    claims: List[ClaimItem] = Field(default_factory=list)
    contradictions: List[ContradictionItem] = Field(default_factory=list)
    uncertain_claims: List[UncertainClaimItem] = Field(default_factory=list)
    things_not_to_claim: List[ThingNotToClaimItem] = Field(default_factory=list)
    version: int = 1
    is_verified: bool = False
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResearchRevisionItem(BaseModel):
    """Audit snapshot preserving creator edits and packet changes."""
    id: str
    packet_id: str
    revision_number: int
    changed_by: str
    change_summary: str
    snapshot: Dict[str, Any]
    created_at: Optional[datetime] = None


class ResearchPacketCreateRequest(BaseModel):
    """Request payload to construct a research packet."""
    opportunity_id: Optional[str] = None
    topic: Optional[str] = None
    source_urls: List[str] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    raw_text: Optional[str] = None
    context: Optional[str] = None


class ResearchPacketUpdateRequest(BaseModel):
    """Request payload for creator edits and manual corrections."""
    summary: Optional[str] = None
    claims: Optional[List[Dict[str, Any]]] = None
    facts: Optional[List[Dict[str, Any]]] = None
    numbers: Optional[List[Dict[str, Any]]] = None
    dates: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    contradictions: Optional[List[Dict[str, Any]]] = None
    uncertain_claims: Optional[List[Dict[str, Any]]] = None
    things_not_to_claim: Optional[List[Dict[str, Any]]] = None
    changed_by: str = "creator"
    change_summary: str = "Manual edit by creator"


class ResearchEngineInput(BaseModel):
    """Input payload for ResearchEngine execution."""
    opportunity_id: Optional[str] = None
    topic: Optional[str] = None
    raw_sources: List[Dict[str, Any]] = Field(default_factory=list)
    raw_text: Optional[str] = None
    context: Optional[str] = None
    dry_run: bool = False


class ResearchEngineResult(BaseModel):
    """Summary of Research Engine run."""
    packet: ResearchPacketItem
    execution_time_ms: float = 0.0
    citations_count: int = 0
    verified_claims_count: int = 0
    uncertain_claims_count: int = 0
    things_not_to_claim_count: int = 0
