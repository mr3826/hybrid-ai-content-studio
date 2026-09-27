from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RefinementType(str, Enum):
    REGENERATE = "regenerate"
    SHORTEN = "shorten"
    EXPAND = "expand"
    MAKE_CLEARER = "make_clearer"
    MORE_EVIDENCE = "more_evidence"


class SectionType(str, Enum):
    HOOK = "hook"
    PROBLEM_CONTEXT = "problem_context"
    METHOD_TEST = "method_test"
    EVIDENCE = "evidence"
    RESULT = "result"
    INTERPRETATION = "interpretation"
    CTA = "cta"


class ScriptSectionOutput(BaseModel):
    id: Optional[str] = None
    section_type: str
    order_index: int
    heading: str
    narration: str
    visual_cue: str = ""
    estimated_seconds: int = 0
    word_count: int = 0
    linked_claim_ids: List[str] = Field(default_factory=list)


class DimensionCheckResult(BaseModel):
    dimension: str # evidence, brand, originality, viewer_value, niche_fit, repetition
    score: float # 0 to 100
    passed: bool
    is_blocking: bool
    notes: str
    flags: List[str] = Field(default_factory=list)


class ScriptQualityVerdict(BaseModel):
    is_approvable: bool
    blocking_reasons: List[str] = Field(default_factory=list)
    dimension_scores: Dict[str, DimensionCheckResult] = Field(default_factory=dict)
    summary: str


class GenerateScriptRequest(BaseModel):
    content_item_id: str
    format: str # short_vertical, youtube_long, social_post, newsletter, article
    working_title: str
    angle: str
    hook_type: str = "bold_claim"
    platform_target: str = "youtube"
    target_duration_sec: int = 60
    # Parent context
    family_title: str
    content_pillar: str = "Core"
    original_value_type: str = "benchmark"
    what_are_we_adding: str = ""
    evidence_claims: List[Dict[str, Any]] = Field(default_factory=list)
    brand_tone: List[str] = Field(default_factory=list)
    banned_cliches: List[str] = Field(default_factory=list)
    voice_rules: List[str] = Field(default_factory=list)
    cta_style: str = "soft_value"
    niche_allowed_topics: List[str] = Field(default_factory=list)
    niche_blocked_topics: List[str] = Field(default_factory=list)


class ScriptDraftOutput(BaseModel):
    id: Optional[str] = None
    content_item_id: str
    format: str
    title: str
    target_platform: str
    target_duration_sec: int
    total_word_count: int
    estimated_duration_sec: int
    status: str
    sections: List[ScriptSectionOutput]
    quality_verdict: Optional[ScriptQualityVerdict] = None


class SectionRefineRequest(BaseModel):
    script_id: str
    section_id: str
    section_type: str
    current_narration: str
    current_visual_cue: str = ""
    refinement_type: RefinementType
    guidance: Optional[str] = None
    linked_claims: List[Dict[str, Any]] = Field(default_factory=list)
    brand_tone: List[str] = Field(default_factory=list)


class SectionRefineOutput(BaseModel):
    section_id: str
    new_narration: str
    new_visual_cue: str
    word_count: int
    estimated_seconds: int
    explanation: str


class ScriptApprovalInput(BaseModel):
    reviewer: str = "creator"
    override_reason: Optional[str] = None


class ScriptApprovalOutput(BaseModel):
    script_id: str
    content_item_id: str
    status: str
    is_approved: bool
    approved_at: datetime
    approved_by: str
    override_reason: Optional[str] = None
