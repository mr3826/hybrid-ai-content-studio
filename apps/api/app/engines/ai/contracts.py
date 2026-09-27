from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TextGenerationRequest(BaseModel):
    """Input contract for standard text generation."""
    prompt: str = Field(..., description="User prompt or instructions")
    system_prompt: Optional[str] = Field(None, description="System instructions or persona")
    task: str = Field(default="generate_text", description="Identifier for task classification")
    prompt_version: str = Field(default="1.0.0", description="Version of the prompt template")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    preferred_provider: Optional[str] = Field(None, description="gemini, qwen, or mock")
    allow_fallback: bool = Field(default=True, description="Whether to trigger fallback on technical error")
    simulate_failure: Optional[str] = Field(None, description="Test hook: rate_limit, server_error, schema_error")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class StructuredGenerationRequest(BaseModel):
    """Input contract for schema-enforced structured JSON generation."""
    prompt: str = Field(..., description="Prompt instructing model to produce JSON")
    response_schema: Dict[str, Any] = Field(..., description="JSON Schema dict defining expected output")
    system_prompt: Optional[str] = Field(None, description="System instructions")
    task: str = Field(default="generate_structured", description="Task classification")
    prompt_version: str = Field(default="1.0.0", description="Prompt version")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    preferred_provider: Optional[str] = Field(None, description="gemini, qwen, or mock")
    allow_fallback: bool = Field(default=True, description="Whether to trigger fallback on schema/technical failure")
    simulate_failure: Optional[str] = Field(None, description="Test hook: rate_limit, server_error, schema_error")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class AnalyzeRequest(BaseModel):
    """Input contract for content analysis, claim extraction, or sentiment auditing."""
    content: str = Field(..., description="Raw text, transcript, or draft to analyze")
    instruction: str = Field(..., description="Analysis instructions")
    criteria: List[str] = Field(default_factory=list, description="Specific criteria or dimensions to audit")
    task: str = Field(default="analyze", description="Task classification")
    prompt_version: str = Field(default="1.0.0", description="Prompt version")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    preferred_provider: Optional[str] = Field(None, description="gemini, qwen, or mock")
    allow_fallback: bool = Field(default=True, description="Whether to trigger fallback on technical failure")
    simulate_failure: Optional[str] = Field(None, description="Test hook")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class AIResponse(BaseModel):
    """Output contract produced by any AI provider adapter or central engine."""
    text: str = Field(..., description="Generated text or stringified response")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="Parsed JSON object if structured")
    provider: str = Field(..., description="gemini, qwen, or mock")
    model: str = Field(..., description="Model string invoked")
    task: str = Field(default="unknown")
    prompt_version: str = Field(default="1.0.0")

    # Usage & Cost
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    cost: float = Field(default=0.0, description="Estimated USD cost")
    latency_ms: float = Field(default=0.0, description="Execution time in milliseconds")

    # Status & Fallback
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    fallback_used: bool = Field(default=False)
    fallback_reason: Optional[str] = None
    primary_provider: Optional[str] = None
    primary_error: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class AIProviderStatus(BaseModel):
    """System health and configuration status for the AI Provider subsystem."""
    mock_mode: bool
    primary_provider: str
    primary_configured: bool
    primary_model: str
    fallback_provider: str
    fallback_configured: bool
    fallback_model: str
    fallback_enabled: bool
    daily_spend_today: float
    daily_budget_limit: float
    budget_exceeded: bool

    model_config = ConfigDict(extra="ignore")
