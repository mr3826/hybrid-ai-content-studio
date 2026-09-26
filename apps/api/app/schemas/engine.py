from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.engines.core.base import EngineHealth, EngineManifest, EngineResult


class EngineSummaryRead(BaseModel):
    id: str
    name: str
    version: str
    description: str
    enabled: bool
    inputs: List[str]
    outputs: List[str]
    dependencies: List[str]
    triggers: List[str]
    supports: Dict[str, bool]
    health: EngineHealth
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    total_runs_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class EngineDetailRead(BaseModel):
    manifest: EngineManifest
    health: EngineHealth
    rules: Dict[str, Any]
    total_runs_count: int = 0
    last_run: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class EngineRunRequest(BaseModel):
    parameters: Dict[str, Any] = {}
    trigger: str = "manual"


class EngineRulesUpdate(BaseModel):
    rules: Dict[str, Any]


class EngineRunRecordRead(BaseModel):
    id: str
    engine_id: str
    engine_version: str
    run_id: str
    trigger: str
    status: str
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    input_count: int
    output_count: int
    rejected_count: int
    error_count: int
    cost: float
    summary: str
    parameters: Dict[str, Any]
    errors: List[str]
    explanations: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)
