from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SceneDraftInput(BaseModel):
    narration: str = Field(..., min_length=1)
    timing_estimate: Optional[float] = Field(None, ge=0.5, le=120.0)
    on_screen_text: Optional[str] = None
    visual_type: Optional[str] = None
    visual_source: Optional[str] = None
    evidence_reference: Optional[str] = None
    asset_rights_record_id: Optional[str] = None
    transition: Optional[str] = "cut"
    status: Optional[str] = "DRAFT"
    notes: Optional[str] = None


class SectionInput(BaseModel):
    id: Optional[str] = None
    section_type: str = "body"
    heading: str = ""
    narration: str = ""
    visual_cue: Optional[str] = None
    linked_claim_ids: List[str] = Field(default_factory=list)


class DecompositionRequest(BaseModel):
    script_id: str
    format: str = "short_vertical"
    title: str = "Script Storyboard"
    sections: List[SectionInput] = Field(default_factory=list)
    target_duration_sec: Optional[int] = 60


class StoryboardSceneVerdict(BaseModel):
    scene_order: int
    visual_type: str
    visual_priority_rank: int
    is_empirical: bool
    timing_estimate: float
    has_evidence_link: bool
    rights_status: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class StoryboardValidationResult(BaseModel):
    total_scenes: int
    total_duration_sec: float
    target_duration_sec: float
    is_timing_valid: bool
    empirical_visual_ratio: float
    missing_assets_count: int
    blocked_rights_count: int
    all_valid: bool
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    scenes: List[StoryboardSceneVerdict] = Field(default_factory=list)
