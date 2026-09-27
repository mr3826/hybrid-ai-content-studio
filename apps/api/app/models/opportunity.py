import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Opportunity(Base, TimestampMixin):
    """Evaluated, scored, and prioritized content opportunity awaiting human gate decisions."""
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    candidate_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("discovered_candidates.id", ondelete="SET NULL"), nullable=True
    )
    trend_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("trend_topics.id", ondelete="SET NULL"), nullable=True
    )

    pillar: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)

    # Workflow Status
    # "needs_review", "watching", "rejected", "approved", "research_ready", "in_production", "ready_to_publish", "published"
    status: Mapped[str] = mapped_column(String(50), default="needs_review", index=True, nullable=False)

    # Primary Composite Scores
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    niche_fit_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    originality_potential: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    audience_usefulness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evergreen_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    commercial_fit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    content_family_potential: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sponsor_relevance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    saturation_penalty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Production estimates
    production_effort: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    estimated_time_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)

    # Angles & Guidance
    suggested_original_angle: Mapped[str] = mapped_column(Text, default="", nullable=False)
    suggested_content_family: Mapped[str] = mapped_column(
        String(100), default="Benchmark Breakdown", nullable=False
    )
    risks: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    why: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(50), default="Research", nullable=False)

    # Score breakdown & references
    score_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_references: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
