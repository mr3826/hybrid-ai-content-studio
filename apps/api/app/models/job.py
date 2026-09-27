import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class StudioJob(Base, TimestampMixin):
    """Local SQLite-backed asynchronous job queue model for worker execution."""
    __tablename__ = "studio_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    engine_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), index=True, default="pending", nullable=False
    )  # pending, running, completed, failed, cancelled
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
