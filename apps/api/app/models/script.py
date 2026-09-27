import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ScriptDraft(Base, TimestampMixin):
    """Domain model representing an evidence-grounded script draft in Script Studio."""
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    content_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Formats: short_vertical, youtube_long, social_post, newsletter, article
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    target_platform: Mapped[str] = mapped_column(String(32), default="youtube", nullable=False)
    target_duration_sec: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    total_word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status: DRAFT, SCRIPT_REVIEW, SCRIPT_APPROVED, REJECTED, ARCHIVED
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False, index=True)

    # 6 Quality Dimensions Breakdown (Evidence, Brand, Originality, Viewer Value, Niche Fit, Repetition)
    quality_scores: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    content_item: Mapped["ContentItem"] = relationship(
        "ContentItem",
        lazy="select",
    )
    sections: Mapped[List["ScriptSection"]] = relationship(
        "ScriptSection",
        back_populates="script",
        cascade="all, delete-orphan",
        order_by="ScriptSection.order_index",
        lazy="select",
    )
    revisions: Mapped[List["ScriptRevision"]] = relationship(
        "ScriptRevision",
        back_populates="script",
        cascade="all, delete-orphan",
        order_by="ScriptRevision.created_at.desc()",
        lazy="select",
    )


class ScriptSection(Base, TimestampMixin):
    """Section-level structural component of a script (Hook, Problem/Context, Method/Test, Evidence, Result, Interpretation, CTA)."""
    __tablename__ = "script_sections"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    script_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Types: hook, problem_context, method_test, evidence, result, interpretation, cta
    section_type: Mapped[str] = mapped_column(String(32), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    heading: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    narration: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visual_cue: Mapped[str] = mapped_column(Text, default="", nullable=False)
    estimated_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    linked_claim_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Relationship
    script: Mapped["ScriptDraft"] = relationship(
        "ScriptDraft",
        back_populates="sections",
        lazy="select",
    )


class ScriptRevision(Base):
    """Versioned audit trail of script iterations, supporting section-level rollback and undo."""
    __tablename__ = "script_revisions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    script_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Trigger: generation, manual_edit, regenerate, shorten, expand, make_clearer, more_evidence, restore
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    script: Mapped["ScriptDraft"] = relationship(
        "ScriptDraft",
        back_populates="revisions",
        lazy="select",
    )
