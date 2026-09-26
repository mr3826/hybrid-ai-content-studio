from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class BenchmarkSignal(BaseModel):
    id: str
    title: str
    metric_value: float = Field(..., description="Numeric signal value (e.g. latency or speed)")
    category: str = "general"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BenchmarkReport(BaseModel):
    id: str
    signal_id: str
    score: float
    passed: bool
    summary: str
    reasons: List[str] = Field(default_factory=list)
