from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

ALLOWED_PLATFORMS = ("youtube", "facebook", "instagram", "tiktok")


class PlatformSetting(Base, TimestampMixin):
    """Platform publishing and launcher settings."""
    __tablename__ = "platform_settings"

    platform: Mapped[str] = mapped_column(String(32), primary_key=True)
    channel_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    channel_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    publishing_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    account_handle: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
