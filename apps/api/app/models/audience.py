import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LeadMagnet(Base, TimestampMixin):
    """Lead magnet asset designed to convert rented social impressions into owned email subscribers."""
    __tablename__ = "lead_magnets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Types: checklist, template, cheat_sheet, code_repository, free_guide, mini_course, tool
    magnet_type: Mapped[str] = mapped_column(String(64), default="cheat_sheet", nullable=False)
    
    landing_page_url: Mapped[str] = mapped_column(String(512), nullable=False)
    cta_copy: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status: ACTIVE, PAUSED, ARCHIVED
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    target_pillar: Mapped[str] = mapped_column(String(128), default="Core", nullable=False)
    
    estimated_value_usd: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)
    total_downloads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    conversions = relationship("AudienceConversion", back_populates="lead_magnet", cascade="all, delete-orphan", lazy="select")


class AudienceConversion(Base, TimestampMixin):
    """Conversion event / snapshot attributing owned audience growth to specific content items and platforms."""
    __tablename__ = "audience_conversions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    lead_magnet_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("lead_magnets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # youtube, tiktok, instagram, facebook, newsletter, direct
    
    utm_source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    conversion_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signups: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    customers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="MANUAL", nullable=False)  # MANUAL, CSV_IMPORT, CAMPAIGN

    # Relationships
    lead_magnet = relationship("LeadMagnet", back_populates="conversions", lazy="selectin")
    content_item = relationship("ContentItem", foreign_keys=[content_item_id], lazy="selectin")
