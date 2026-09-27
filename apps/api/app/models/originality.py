import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class OriginalityPlan(Base, TimestampMixin):
    """Enforces channel contribution ('What are WE adding?') and blocks generic summaries."""

    __tablename__ = "originality_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id = Column(String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    packet_id = Column(String(36), ForeignKey("research_packets.id", ondelete="SET NULL"), nullable=True, index=True)
    topic = Column(String(512), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)

    # Core Originality Pillars
    originality_type = Column(String(64), nullable=False, index=True)
    what_are_we_adding = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=False, default="")

    # Status & Gate: "needs_review", "approved", "rejected", "not_ready"
    status = Column(String(50), nullable=False, default="needs_review", index=True)
    is_generic_summary = Column(Boolean, nullable=False, default=False, index=True)
    confidence_score = Column(Float, nullable=False, default=80.0)

    # Experiments suggested or planned
    suggested_experiments = Column(JSON, nullable=False, default=list)

    # Human Gate Audit
    review_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    experiments = relationship("Experiment", back_populates="originality_plan")


class ExperimentAttachment(Base):
    """Evidence or benchmark artifact attached to an experiment."""

    __tablename__ = "experiment_attachments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_type = Column(String(50), nullable=False, index=True)  # json, csv, screenshot, image, screen_recording, terminal_output, code_snippet
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False, default="application/octet-stream")
    size_bytes = Column(Integer, nullable=False, default=0)
    content_snippet = Column(Text, nullable=True)  # small inline snippet preview
    caption = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    experiment = relationship("Experiment", back_populates="attachments")
