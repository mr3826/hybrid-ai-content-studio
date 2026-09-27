import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Float, Integer, JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class EngineRunRecord(Base, TimestampMixin):
    """Execution history and audit log for Engine runs."""
    __tablename__ = "engine_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    engine_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rules_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)  # completed, failed, dry_run

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    input_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    errors: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    explanations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
