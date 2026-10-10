import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class AIInvocationLog(Base, TimestampMixin):
    """Audit and telemetry log for all centralized LLM invocations."""
    __tablename__ = "ai_invocation_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # gemini/mock and historical provider IDs
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # generate_text, generate_structured, analyze, etc.
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")

    # Usage & Cost
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Provider and historical routing compatibility metadata
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    fallback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    primary_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata & Sanitized Telemetry (Secrets never logged!)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
