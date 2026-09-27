import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ContentFamily(Base, TimestampMixin):
    """Domain model representing a Content Family.
    
    Replaces 'Project = one piece of content' with:
    'Content Family = one research/evidence/originality investment'
    which generates multiple child content items from shared empirical foundation.
    """
    __tablename__ = "content_families"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    research_packet_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("research_packets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    originality_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("originality_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    primary_experiment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # State Machine: DRAFT, READY_FOR_CONTENT, ACTIVE, COMPLETED, ARCHIVED
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False, index=True)
    content_pillar: Mapped[str] = mapped_column(String(128), default="Core", nullable=False)
    original_value_type: Mapped[str] = mapped_column(String(64), default="benchmark", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Family-Level Production Economics
    research_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experiment_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ai_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    media_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    manual_time_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    local_compute_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    opportunity: Mapped[Optional["Opportunity"]] = relationship(
        "Opportunity",
        foreign_keys=[topic_id],
        lazy="select",
    )
    research_packet: Mapped[Optional["ResearchPacket"]] = relationship(
        "ResearchPacket",
        foreign_keys=[research_packet_id],
        lazy="select",
    )
    originality_plan: Mapped[Optional["OriginalityPlan"]] = relationship(
        "OriginalityPlan",
        foreign_keys=[originality_plan_id],
        lazy="select",
    )
    primary_experiment: Mapped[Optional["Experiment"]] = relationship(
        "Experiment",
        foreign_keys=[primary_experiment_id],
        lazy="select",
    )
    items: Mapped[List["ContentItem"]] = relationship(
        "ContentItem",
        back_populates="family",
        cascade="all, delete-orphan",
        order_by="ContentItem.created_at",
        lazy="select",
    )


class ContentItem(Base, TimestampMixin):
    """Child content item within a Content Family sharing the factual foundation.
    
    Each child is independently editable and adapted to its specific format and platform target.
    """
    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    content_family_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("content_families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Formats: short_vertical, youtube_long, social_post, newsletter, article
    format: Mapped[str] = mapped_column(String(32), nullable=False)

    # Platform targets: youtube, facebook, instagram, tiktok, cross_platform, none
    platform_target: Mapped[str] = mapped_column(String(32), default="youtube", nullable=False)

    working_title: Mapped[str] = mapped_column(String(256), nullable=False)
    angle: Mapped[str] = mapped_column(Text, nullable=False)

    # Hook types: curiosity_gap, bold_claim, problem_agitation, surprising_stat, story_open, direct_value
    hook_type: Mapped[str] = mapped_column(String(64), default="bold_claim", nullable=False)

    # State Machine: PLANNED, DRAFT, SCRIPT_REVIEW, SCRIPT_APPROVED, READY_FOR_EXPORT, EXPORTED, READY_TO_PUBLISH, PUBLISHED, REJECTED
    status: Mapped[str] = mapped_column(String(32), default="PLANNED", nullable=False, index=True)

    script_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Child-Specific Incremental Production Economics
    incremental_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    manual_time_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    local_compute_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Original Value & Viewer Value Connection
    original_value_connection: Mapped[str] = mapped_column(Text, default="", nullable=False)
    viewer_value: Mapped[str] = mapped_column(Text, default="", nullable=False)

    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    family: Mapped["ContentFamily"] = relationship("ContentFamily", back_populates="items")
    evidence_selections: Mapped[List["ContentItemEvidenceSelection"]] = relationship(
        "ContentItemEvidenceSelection",
        back_populates="content_item",
        cascade="all, delete-orphan",
        lazy="select",
    )


class ContentItemEvidenceSelection(Base):
    """Mechanism for child items to select subsets of the parent family's approved evidence
    without duplicating Claim records.
    """
    __tablename__ = "content_item_evidence_selections"

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
    claim_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relevance_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    content_item: Mapped["ContentItem"] = relationship("ContentItem", back_populates="evidence_selections")
    claim: Mapped["Claim"] = relationship("Claim", foreign_keys=[claim_id], lazy="select")
