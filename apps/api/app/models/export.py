import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExportPackage(Base, TimestampMixin):
    """Domain model representing a generated offline/manual export package.
    
    Contains markdown documents, structured platform texts, asset requirements,
    and a cryptographically checksummed manifest.
    """
    __tablename__ = "export_packages"

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
    package_slug: Mapped[str] = mapped_column(String(256), nullable=False)
    export_dir: Mapped[str] = mapped_column(String(512), nullable=False)
    manifest_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    files: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    content_item: Mapped["ContentItem"] = relationship(
        "ContentItem",
        lazy="select",
    )
    publications: Mapped[List["PlatformPublication"]] = relationship(
        "PlatformPublication",
        back_populates="export_package",
        lazy="select",
    )


class PlatformPublication(Base, TimestampMixin):
    """Tracks per-platform publication readiness, checklist state, copyable metadata,
    and manual post-publication URL/audit records.
    """
    __tablename__ = "platform_publications"

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
    export_package_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("export_packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Platforms: youtube, facebook, instagram, tiktok
    platform: Mapped[str] = mapped_column(String(32), nullable=False)

    # Statuses: NOT_READY, READY, PUBLISHED, SKIPPED
    status: Mapped[str] = mapped_column(String(32), default="NOT_READY", nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    caption: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hashtags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    pinned_comment: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # 7-Point Publishing Checklist:
    # {
    #   "media_ready": bool,
    #   "thumbnail_ready": bool,
    #   "title_caption_ready": bool,
    #   "sources_checked": bool,
    #   "affiliate_disclosure_needed": bool,
    #   "ai_disclosure_recommended": bool,
    #   "asset_rights_verified": bool
    # }
    checklist: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    post_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    content_item: Mapped["ContentItem"] = relationship(
        "ContentItem",
        lazy="select",
    )
    export_package: Mapped[Optional["ExportPackage"]] = relationship(
        "ExportPackage",
        back_populates="publications",
        lazy="select",
    )
