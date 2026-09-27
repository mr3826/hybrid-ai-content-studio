import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class RssFeed(Base, TimestampMixin):
    """Configured RSS or Atom content discovery source."""
    __tablename__ = "rss_feeds"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(128), default="General", nullable=False)
    trust_weight: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DiscoveredCandidate(Base, TimestampMixin):
    """Normalized, deduplicated, and cross-source grouped candidate story discovered via feeds."""
    __tablename__ = "discovered_candidates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    canonical_url: Mapped[str] = mapped_column(String(2048), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    primary_source: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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

    source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sources: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    authority_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)

    pillar: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    niche_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_in_niche: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    niche_verdict: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    status: Mapped[str] = mapped_column(
        String(32), default="candidate", index=True, nullable=False
    )  # candidate, rejected, promoted_to_opportunity
    raw_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
