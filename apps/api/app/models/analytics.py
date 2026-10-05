import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PublicationMetricsSnapshot(Base, TimestampMixin):
    """Domain model tracking manual platform publication performance snapshots,
    retention curves, engagement data, and business economics.
    """
    __tablename__ = "publication_metrics_snapshots"

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
    platform_publication_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("platform_publications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    snapshot_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    snapshot_label: Mapped[str] = mapped_column(String(64), default="24h", nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watch_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_view_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retention_rate_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hook_retention_3s_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hook_retention_30s_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_estimated_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="MANUAL", nullable=False)
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    content_item: Mapped["ContentItem"] = relationship(
        "ContentItem",
        lazy="select",
    )
    platform_publication: Mapped[Optional["PlatformPublication"]] = relationship(
        "PlatformPublication",
        lazy="select",
    )
