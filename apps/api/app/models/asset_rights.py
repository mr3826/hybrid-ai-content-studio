import uuid
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AssetRightsStatus:
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"
    REQUIRES_ATTRIBUTION = "REQUIRES_ATTRIBUTION"
    DO_NOT_USE = "DO_NOT_USE"

    ALL = [VERIFIED, UNKNOWN, REQUIRES_ATTRIBUTION, DO_NOT_USE]


class CommercialUseStatus:
    ALLOWED = "ALLOWED"
    PROHIBITED = "PROHIBITED"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"

    ALL = [ALLOWED, PROHIBITED, RESTRICTED, UNKNOWN]


class AssetRightsRecord(Base, TimestampMixin):
    """Domain model representing copyright, license, and provenance documentation
    for external and generated visual, audio, or code assets.
    """
    __tablename__ = "asset_rights_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    content_item_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("content_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    asset_type: Mapped[str] = mapped_column(
        String(64),
        default="image",
        nullable=False,
        index=True,
    )
    uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source: Mapped[str] = mapped_column(String(256), nullable=False)
    creator_provider: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    license_type: Mapped[str] = mapped_column(
        String(128),
        default="Unknown",
        nullable=False,
    )
    commercial_use_status: Mapped[str] = mapped_column(
        String(32),
        default=CommercialUseStatus.UNKNOWN,
        nullable=False,
    )
    attribution_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    attribution_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    license_proof: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expiry_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    ai_tool: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=AssetRightsStatus.UNKNOWN,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationship to ContentItem if linked
    content_item = relationship(
        "ContentItem",
        foreign_keys=[content_item_id],
        lazy="select",
    )
