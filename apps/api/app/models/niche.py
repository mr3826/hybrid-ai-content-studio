from typing import Any, Dict, List
from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

SINGLETON_NICHE_ID = "primary"


class NicheProfile(Base, TimestampMixin):
    """Single Niche Profile (Singleton).
    The studio allows exactly ONE active niche. Multi-tenant workspace switching is forbidden.
    """
    __tablename__ = "niche_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=SINGLETON_NICHE_ID)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    one_sentence_definition: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(Text, nullable=False)
    audience_regions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    primary_problems: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    adjacent_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    must_have_signals: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    negative_keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_source_types: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    content_pillars: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    commercial_intent_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    evergreen_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
