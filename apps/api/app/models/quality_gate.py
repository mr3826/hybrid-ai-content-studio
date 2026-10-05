import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QualityGateAudit(Base, TimestampMixin):
    """Domain model representing the comprehensive 9-dimension Final Creator Quality Gate audit.
    
    Dimensions:
    1. Evidence Quality
    2. Brand Fit
    3. Originality
    4. Viewer Value
    5. Niche Fit
    6. Repetition Intelligence
    7. Asset Rights
    8. Technical Media QC
    9. Estimated Cost & Production Economics
    """
    __tablename__ = "quality_gate_audits"

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
    script_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("scripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Status: PENDING, PASSED, WARNING, BLOCKED, FINAL_APPROVED
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 9 Dimension Scores & Data (JSON dictionaries)
    evidence_quality: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    brand_fit: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    originality: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    viewer_value: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    niche_fit: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    repetition_intelligence: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    asset_rights: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    media_qc: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    estimated_cost: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Actionable recommendations & direct routing
    actionable_recommendations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Human Gate Decision
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    content_item = relationship("ContentItem", backref="quality_gate_audits", lazy="select")
    script = relationship("ScriptDraft", backref="quality_gate_audits", lazy="select")
