from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LessonType(str, Enum):
    HOOK_OPTIMIZATION = "hook_optimization"
    PACING_ADJUSTMENT = "pacing_adjustment"
    BANNED_PHRASE_ADDITION = "banned_phrase_addition"
    PREFERRED_VOCABULARY_ADDITION = "preferred_vocabulary_addition"
    FORMAT_RECOMMENDATION = "format_recommendation"
    TOPIC_REINFORCEMENT = "topic_reinforcement"
    ANGLE_GUIDANCE = "angle_guidance"
    CTA_REFINEMENT = "cta_refinement"


class ImpactLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class LessonStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


class ProposedAdjustment(BaseModel):
    target: str = Field(..., description="Target system: brand_profile, brand_memory, brand_exemplar, or rules")
    field: str = Field(..., description="Field name in target, e.g. avoid_vocabulary, banned_cliches, preferred_vocabulary, cta_style")
    action: str = Field(..., description="Action: append, update, record_memory, add_exemplar")
    value: Any = Field(..., description="Value or dictionary payload to apply")
    summary: str = Field(..., description="Human-readable explanation of what this adjustment will change")


class FeedbackLessonCreateRequest(BaseModel):
    content_item_id: Optional[str] = None
    lesson_type: LessonType = LessonType.HOOK_OPTIMIZATION
    title: str = Field(..., min_length=3, max_length=255)
    observation: str = Field(..., min_length=10)
    impact_level: ImpactLevel = ImpactLevel.MEDIUM
    confidence_score: float = Field(0.8, ge=0.0, le=1.0)
    evidence_data: Dict[str, Any] = Field(default_factory=dict)
    proposed_adjustment: ProposedAdjustment


class FeedbackLessonResponse(BaseModel):
    id: str
    content_item_id: Optional[str] = None
    content_item_title: Optional[str] = None
    lesson_type: str
    title: str
    observation: str
    impact_level: str
    confidence_score: float
    evidence_data: Dict[str, Any] = Field(default_factory=dict)
    proposed_adjustment: Dict[str, Any] = Field(default_factory=dict)
    status: str
    creator_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FeedbackActionRequest(BaseModel):
    creator_notes: Optional[str] = Field(None, description="Creator feedback, justification, or review notes")


class FeedbackSummaryResponse(BaseModel):
    total_lessons: int
    pending_count: int
    approved_count: int
    applied_count: int
    rejected_count: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_impact: Dict[str, int] = Field(default_factory=dict)


class FeedbackEvaluateRequest(BaseModel):
    days: int = Field(30, ge=1, le=365)
    min_impressions: int = Field(50, ge=0)


class FeedbackEvaluateResponse(BaseModel):
    evaluated_snapshots: int
    lessons_generated: int
    lessons: List[FeedbackLessonResponse] = Field(default_factory=list)


class FeedbackExplainResponse(BaseModel):
    lesson_id: str
    lesson_type: str
    title: str
    observation: str
    reasoning: str
    data_source: str
    rule_triggered: str
    human_gate_required: bool = True
