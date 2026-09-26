from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EngineHealth(BaseModel):
    status: str = Field(description="healthy, degraded, failing")
    message: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


class EngineContext(BaseModel):
    run_id: str
    dry_run: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)


class EngineResult(BaseModel):
    engine_id: str
    engine_version: str
    run_id: str
    success: bool
    started_at: datetime
    ended_at: datetime
    input_count: int = 0
    output_count: int = 0
    rejected_count: int = 0
    error_count: int = 0
    cost: float = 0.0
    summary: str
    outputs: List[Any] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class EngineExplanation(BaseModel):
    result_id: str
    summary: str
    factors: List[Dict[str, Any]] = Field(default_factory=list)


class BaseEngine(ABC):
    id: str
    name: str
    version: str

    @abstractmethod
    def validate_config(self) -> None:
        """Validate engine configuration or rules."""
        pass

    @abstractmethod
    def health(self) -> EngineHealth:
        """Perform active health check."""
        pass

    @abstractmethod
    async def run(self, context: EngineContext) -> EngineResult:
        """Execute the engine logic with side effects."""
        pass

    @abstractmethod
    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Execute without persisting side effects."""
        pass

    @abstractmethod
    def explain(self, result_id: str) -> EngineExplanation:
        """Provide detailed human-readable breakdown of an output decision."""
        pass
