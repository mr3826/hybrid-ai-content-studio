from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BrandQAInput(BaseModel):
    """Input draft, script, or copy to evaluate against the single BrandProfile."""
    id: Optional[str] = Field(default=None, description="Draft or item identifier")
    title: str = Field(default="", description="Headline or title")
    body: str = Field(..., description="Draft text, video script, or post copy")
    hook: Optional[str] = Field(default=None, description="Opening hook sentence or first 5 seconds")
    cta: Optional[str] = Field(default=None, description="Call to action text")
    platform: Optional[str] = Field(default="all", description="Target platform (youtube_shorts, tiktok, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary context metadata")


class BrandViolation(BaseModel):
    """Specific brand guideline infraction detected in draft."""
    rule_type: str = Field(..., description="banned_cliche, avoid_vocabulary, unsupported_claim, tone_mismatch, excessive_hype")
    severity: str = Field(default="critical", description="critical, warning, or suggestion")
    matched_phrase: str = Field(..., description="Offending word, phrase, or pattern detected")
    message: str = Field(..., description="Human-readable explanation of why this violates brand identity")
    suggestion: str = Field(default="", description="Recommended action or replacement phrasing")


class BrandQAVerdict(BaseModel):
    """Quality assurance verdict produced by the Brand Engine."""
    id: str = Field(..., description="Unique verdict execution ID")
    input_id: Optional[str] = Field(default=None, description="ID of the evaluated item if provided")
    on_brand: bool = Field(..., description="True if draft passes all critical brand gates")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted brand adherence score [0.0 - 100.0]")
    
    # 6 Formal QA Dimensions
    tone_score: float = Field(..., ge=0.0, le=100.0, description="Tone & voice score")
    vocabulary_score: float = Field(..., ge=0.0, le=100.0, description="Vocabulary adherence score")
    repetition_score: float = Field(..., ge=0.0, le=100.0, description="Redundancy and memory repetition score")
    audience_fit_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Target audience fit score")
    cta_fit_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Call to action fit score")
    platform_fit_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Platform adaptation fit score")
    dimensions: Dict[str, float] = Field(default_factory=dict, description="Summary of the 6 formal QA dimension scores")

    # Granular sub-scores & metadata
    cliche_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Cliché compliance score")
    claim_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Claim & evidence score")
    repetition_warnings: List[str] = Field(default_factory=list, description="Intelligent warnings regarding repetitive patterns")
    matched_memory_items: List[Dict[str, Any]] = Field(default_factory=list, description="Brand memory items matched")

    violations: List[BrandViolation] = Field(default_factory=list, description="Detected violations")
    matched_preferred_words: List[str] = Field(default_factory=list, description="Approved preferred brand words found")
    matched_avoid_words: List[str] = Field(default_factory=list, description="Avoided words found")
    matched_cliches: List[str] = Field(default_factory=list, description="Banned clichés found")
    suggested_fixes: List[str] = Field(default_factory=list, description="Actionable recommendations")
    exemplar_matches: List[Dict[str, Any]] = Field(default_factory=list, description="Similar approved brand exemplars")
    factors: List[Dict[str, Any]] = Field(default_factory=list, description="Component score factor breakdown")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
