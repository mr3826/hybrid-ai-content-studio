import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class TrendTopic(Base, TimestampMixin):
    """Emerging or active trend cluster identified within the niche."""
    __tablename__ = "trend_topics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    topic_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pillar: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)

    keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    trend_score: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    mention_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    distinct_sources_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_diversity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_authority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    velocity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    velocity_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    historical_baseline: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    manual_boost: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True, nullable=False)

    signal_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    source_breakdown: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    history: Mapped[List["TrendHistory"]] = relationship(
        "TrendHistory", back_populates="topic", cascade="all, delete-orphan", order_by="TrendHistory.recorded_at.desc()"
    )


class TrendHistory(Base, TimestampMixin):
    """Historical snapshot tracking topic score and velocity over time."""
    __tablename__ = "trend_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    topic_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("trend_topics.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    trend_score: Mapped[float] = mapped_column(Float, nullable=False)
    momentum_score: Mapped[float] = mapped_column(Float, nullable=False)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False)
    velocity: Mapped[float] = mapped_column(Float, nullable=False)
    snapshot_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    topic: Mapped["TrendTopic"] = relationship("TrendTopic", back_populates="history")
