from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OriginalityType(str, Enum):
    TOOL_TEST = "tool_test"
    BENCHMARK = "benchmark"
    COST_COMPARISON = "cost_comparison"
    WORKFLOW_DEMONSTRATION = "workflow_demonstration"
    BEFORE_AFTER = "before_after"
    IMPLEMENTATION_ATTEMPT = "implementation_attempt"
    MULTI_SOURCE_SYNTHESIS = "multi_source_synthesis"
    ORIGINAL_FRAMEWORK = "original_framework"
    ORIGINAL_CHART_DATA_ANALYSIS = "original_chart_data_analysis"
    PRACTICAL_TUTORIAL = "practical_tutorial"
    FAILURE_ANALYSIS = "failure_analysis"
    CLEARLY_LABELED_OPINION = "clearly_labeled_opinion"


class CreatePlanRequest(BaseModel):
    """Input contract to create or propose an originality plan."""
    topic: str = Field(..., description="Content topic or working title")
    originality_type: str = Field(..., description="One of the 12 supported originality types")
    what_are_we_adding: str = Field(..., description="Explicit answer to: What are WE adding?")
    why_it_matters: str = Field(default="", description="Why this original contribution matters to the audience")
    opportunity_id: Optional[str] = Field(None, description="Optional opportunity ID")
    packet_id: Optional[str] = Field(None, description="Optional research packet ID")
    suggested_experiments: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class PlanEvaluationResult(BaseModel):
    """Quality gate result evaluating whether the topic adds original channel value."""
    is_ready: bool = Field(..., description="Whether the topic is approved to proceed into script studio")
    is_generic_summary: bool = Field(..., description="True if input is merely a recap of external news")
    status: str = Field(..., description="needs_review, approved, rejected, not_ready")
    rejection_reason: Optional[str] = Field(None)
    confidence_score: float = Field(default=80.0)
    originality_type: str
    what_are_we_adding: str

    model_config = ConfigDict(extra="ignore")


class CreateExperimentRequest(BaseModel):
    """Input contract for storing an empirical experiment in the workspace."""
    title: str = Field(..., description="Experiment title or benchmark scenario")
    hypothesis: str = Field(..., description="Expected outcome or test hypothesis")
    method: str = Field(..., description="Specific reproduction or testing method")
    question: Optional[str] = Field(None, description="Inquiry question being tested")
    dataset_sample: Optional[str] = Field(None, description="Input data or sample dataset used")
    tools_models: List[str] = Field(default_factory=list, description="Hardware, local models, or software tested")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters or flags")
    results: Dict[str, Any] = Field(default_factory=dict, description="Observed quantitative/qualitative outputs")
    failures: List[str] = Field(default_factory=list, description="Encountered errors, crash logs, or limitations")
    latency_ms: Optional[float] = Field(default=0.0)
    cost_usd: Optional[float] = Field(default=0.0)
    screenshots_files: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None)
    conclusion: Optional[str] = Field(default=None)
    status: str = Field(default="completed", description="completed, draft, running, verified, inconclusive")
    opportunity_id: Optional[str] = Field(None)
    originality_plan_id: Optional[str] = Field(None)

    model_config = ConfigDict(extra="ignore")


class CreateAttachmentRequest(BaseModel):
    """Contract for attaching artifacts (JSON, CSV, screenshots, code snippets) to an experiment."""
    attachment_type: str = Field(..., description="json, csv, screenshot, image, screen_recording, terminal_output, code_snippet")
    filename: str = Field(...)
    file_path: str = Field(...)
    mime_type: str = Field(default="application/octet-stream")
    size_bytes: int = Field(default=0)
    content_snippet: Optional[str] = Field(None, description="Optional text preview or small snippet")
    caption: Optional[str] = Field(None)

    model_config = ConfigDict(extra="ignore")
