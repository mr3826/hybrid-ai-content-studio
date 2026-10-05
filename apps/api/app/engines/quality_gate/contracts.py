from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DimensionStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class QualityDimension(BaseModel):
    id: str = Field(description="Identifier for dimension, e.g. evidence_quality, brand_fit")
    name: str = Field(description="Human readable name")
    score: float = Field(ge=0.0, le=100.0, description="Evaluated score 0 to 100")
    status: DimensionStatus = Field(default=DimensionStatus.PASSED)
    summary: str = Field(description="Summary verdict for this dimension")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Key empirical numbers")
    details: List[str] = Field(default_factory=list, description="Observations and rule evaluations")


class CorrectionRoute(BaseModel):
    action_type: str = Field(
        description="One of: return_to_script, return_to_scene, replace_asset, fix_unsupported_claim, rerender_segment"
    )
    title: str
    description: str
    target_route: str = Field(description="Frontend navigation target")
    severity: str = Field(default="medium", description="high, medium, low")


class QualityGateAuditResponse(BaseModel):
    id: Optional[str] = None
    content_item_id: str
    script_id: Optional[str] = None
    item_title: str
    format: str
    platform_target: str
    status: str
    overall_score: float
    is_approved: bool
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    override_reason: Optional[str] = None

    # The 9 Dimension Breakdowns
    dimensions: List[QualityDimension] = Field(default_factory=list)

    # Actionable direct corrections
    recommendations: List[CorrectionRoute] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FinalApprovalRequest(BaseModel):
    approved_by: Optional[str] = "Creator"
    notes: Optional[str] = None
    override_reason: Optional[str] = None


class FinalApprovalResponse(BaseModel):
    content_item_id: str
    script_id: Optional[str] = None
    status: str
    is_approved: bool
    unlocked_export: bool
    approved_by: str
    approved_at: datetime
    message: str
