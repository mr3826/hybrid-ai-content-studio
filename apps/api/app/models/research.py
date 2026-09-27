import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class ResearchPacket(Base, TimestampMixin):
    """Traceable, evidence-grounded research packet for a content opportunity."""
    __tablename__ = "research_packets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    opportunity_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    topic: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Source tracking
    primary_sources: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    supporting_sources: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Granular Evidence Categories
    facts: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    numbers: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    dates: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    entities: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Core Claim Traceability: Every claim must be source-backed, explicitly_uncertain, or manually_entered
    claims: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    contradictions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    uncertain_claims: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    things_not_to_claim: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Versioning & Quality Gates
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    revisions: Mapped[List["ResearchRevision"]] = relationship(
        "ResearchRevision",
        back_populates="packet",
        cascade="all, delete-orphan",
        order_by="desc(ResearchRevision.revision_number)",
    )


class ResearchRevision(Base):
    """Historical revision snapshot preserving creator edits and audit history."""
    __tablename__ = "research_revisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    packet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_packets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), default="creator", nullable=False)
    change_summary: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    packet: Mapped["ResearchPacket"] = relationship("ResearchPacket", back_populates="revisions")
