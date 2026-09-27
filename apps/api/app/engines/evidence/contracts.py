from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ClaimTypeLiteral = Literal[
    "external_fact",
    "original_measurement",
    "derived_conclusion",
    "opinion",
    "prediction_speculation",
]

VerificationStatusLiteral = Literal[
    "verified",
    "unsupported",
    "labeled_opinion",
    "overridden",
]


class SourceNode(BaseModel):
    """Source entity in provenance graph."""
    source_id: Optional[str] = None
    url: str
    title: str
    domain: str
    source_type: str = "primary"  # primary, supporting, experiment
    trust_weight: float = 1.0
    quote: Optional[str] = None
    confidence: float = 0.9


class MeasurementNode(BaseModel):
    """Measurement metric in provenance graph."""
    metric: str
    value: float
    unit: Optional[str] = None
    context: Optional[str] = None


class RunNode(BaseModel):
    """Execution run in provenance graph."""
    run_id: str
    run_number: int
    cost_usd: float = 0.0
    execution_time_ms: int = 0
    status: str = "success"
    measurements: List[MeasurementNode] = Field(default_factory=list)


class ExperimentNode(BaseModel):
    """Empirical experiment node in provenance graph."""
    experiment_id: str
    title: str
    hypothesis: str
    method: str
    conclusion_summary: Optional[str] = None
    confidence: float = 0.95
    runs: List[RunNode] = Field(default_factory=list)


class ContentUsageNode(BaseModel):
    """Usage of claim within script or scene."""
    content_claim_id: str
    content_id: str
    section_id: str
    quote_in_script: str
    verification_status: VerificationStatusLiteral
    is_overridden: bool = False
    override_reason: Optional[str] = None


class ProvenanceTrace(BaseModel):
    """Complete traceable chain from source through experiment to script section."""
    claim_id: str
    claim_text: str
    claim_type: ClaimTypeLiteral
    is_verified: bool
    confidence: float
    sources: List[SourceNode] = Field(default_factory=list)
    experiments: List[ExperimentNode] = Field(default_factory=list)
    content_usages: List[ContentUsageNode] = Field(default_factory=list)


class CoverageReport(BaseModel):
    """Evidence coverage metrics and quality gate decision."""
    total_claims: int
    factual_claims: int
    primary_source_backed: int
    supporting_source_backed: int
    original_test_backed: int
    opinions_labeled: int
    overridden_count: int
    unsupported: int
    coverage_percent: float
    gate_passed: bool
    explanation: Optional[str] = None


class CreateClaimInput(BaseModel):
    text: str
    claim_type: ClaimTypeLiteral = "external_fact"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    packet_id: Optional[str] = None
    is_verified: bool = False


class LinkEvidenceInput(BaseModel):
    quote: str
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_type: str = "primary"
    trust_weight: float = 1.0
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    notes: Optional[str] = None


class OverrideClaimInput(BaseModel):
    override_reason: str = Field(..., min_length=5, description="Mandatory reason for creator override")


class LabelOpinionInput(BaseModel):
    claim_type: Literal["opinion", "prediction_speculation"] = "opinion"


class CreateExperimentInput(BaseModel):
    title: str
    hypothesis: str
    method: str
    opportunity_id: Optional[str] = None
    tools_models: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AddRunInput(BaseModel):
    run_number: int = 1
    execution_time_ms: int = 0
    cost_usd: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None
    measurements: List[Dict[str, Any]] = Field(default_factory=list)


class AddConclusionInput(BaseModel):
    summary: str
    claim_id: Optional[str] = None
    confidence: float = 0.95


class EvidenceEngineInput(BaseModel):
    packet_id: Optional[str] = None
    content_id: Optional[str] = None
    custom_claims: Optional[List[Dict[str, Any]]] = None


class EvidenceEngineOutput(BaseModel):
    coverage_report: CoverageReport
    traces: List[ProvenanceTrace] = Field(default_factory=list)
