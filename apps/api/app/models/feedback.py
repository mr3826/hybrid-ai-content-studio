import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class FeedbackLesson(Base, TimestampMixin):
    """Creator-Guided Feedback Lesson.
    Closed feedback loop analyzing performance lessons, updating brand memory/rules,
    generating human-approved editorial adjustment proposals, and preventing unvetted automated self-modification.
    """
    __tablename__ = "feedback_lessons"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    content_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    lesson_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # hook_optimization, pacing_adjustment, banned_phrase_addition, preferred_vocabulary_addition, format_recommendation, topic_reinforcement, angle_guidance, cta_refinement
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    impact_level: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)  # HIGH, MEDIUM, LOW
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    
    evidence_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    proposed_adjustment: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Structure of proposed_adjustment:
    # {
    #   "target": "brand_profile" | "brand_memory" | "brand_exemplar" | "rules",
    #   "field": "avoid_vocabulary" | "banned_cliches" | "preferred_vocabulary" | "voice_rules" | "claim_rules" | "cta_style",
    #   "action": "append" | "update" | "record_memory" | "add_exemplar",
    #   "value": "...",
    #   "summary": "..."
    # }

    status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False, index=True
    )  # PENDING, APPROVED, REJECTED, APPLIED
    
    creator_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    content_item = relationship("ContentItem", foreign_keys=[content_item_id], lazy="selectin")
