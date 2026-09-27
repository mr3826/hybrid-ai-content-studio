import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

SINGLETON_BRAND_ID = "primary"


class BrandProfile(Base, TimestampMixin):
    """Single Brand Profile (Singleton).
    All daily content inherits its tone, voice, vocabulary, visual identity, and editorial policies.
    """
    __tablename__ = "brand_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=SINGLETON_BRAND_ID)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_promise: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(Text, nullable=False)

    tone: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    voice_rules: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_vocabulary: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    avoid_vocabulary: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    banned_cliches: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    claim_rules: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    cta_style: Mapped[str] = mapped_column(Text, default="", nullable=False)
    humor_policy: Mapped[str] = mapped_column(Text, default="", nullable=False)
    controversy_policy: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sponsor_policy: Mapped[str] = mapped_column(Text, default="", nullable=False)
    affiliate_disclosure_style: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Monetization Metadata
    default_lead_magnet: Mapped[str] = mapped_column(Text, default="", nullable=False)
    newsletter_cta: Mapped[str] = mapped_column(Text, default="", nullable=False)
    digital_product_cta: Mapped[str] = mapped_column(Text, default="", nullable=False)

    visual_identity: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    platform_adaptations: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class BrandMemoryItem(Base, TimestampMixin):
    """Brand Memory: tracks recent approved hooks, CTAs, topics, tested products,
    conclusions, visual patterns, frequently used phrases, and thumbnail wording.
    Ensures 'same identity, different execution' without repetitive fatigue.
    """
    __tablename__ = "brand_memory"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    memory_type: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )  # hook, cta, topic, tested_product, conclusion, visual_pattern, frequent_phrase, thumbnail_wording
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usage_count: Mapped[int] = mapped_column(default=1, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )



class BrandExemplar(Base, TimestampMixin):
    """Brand exemplars: approved hooks, scripts, captions, and do/don't examples."""
    __tablename__ = "brand_exemplars"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # approved_hook, approved_script, approved_caption, do_example, dont_example
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
