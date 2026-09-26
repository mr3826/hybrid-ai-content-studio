import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import JSON, String, Text
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

    visual_identity: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    platform_adaptations: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


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
