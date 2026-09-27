from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    job_type: str = Field(..., description="Job type, e.g. engine_run, audio_generation, video_render")
    engine_id: Optional[str] = Field(default=None, description="Engine identifier if applicable")
    project_id: Optional[str] = Field(default=None, description="Target project identifier if applicable")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job execution payload parameters")


class JobRead(BaseModel):
    id: str
    job_type: str
    engine_id: Optional[str] = None
    project_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str
    attempts: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    jobs: List[JobRead]
    total: int
