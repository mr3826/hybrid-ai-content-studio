import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class MediaPackageStatus:
    DRAFT = "DRAFT"
    SYNTHESIZING = "SYNTHESIZING"
    SYNTHESIZED = "SYNTHESIZED"
    RENDERING = "RENDERING"
    READY = "READY"
    MOCK = "MOCK"
    FAILED = "FAILED"


class MediaResolution:
    VERTICAL_9_16 = "1080x1920"
    HORIZONTAL_16_9 = "1920x1080"


class MediaPackage(Base):
    """Represents a compiled media package including voice tracks, subtitles, and rendered video."""

    __tablename__ = "media_packages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    script_id = Column(String(36), ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    content_item_id = Column(String(36), ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True, index=True)

    format = Column(String(50), nullable=False, default="short_vertical")
    resolution = Column(String(20), nullable=False, default=MediaResolution.VERTICAL_9_16)
    status = Column(String(30), nullable=False, default=MediaPackageStatus.DRAFT, index=True)

    total_duration_sec = Column(Float, nullable=False, default=0.0)

    audio_path = Column(String(500), nullable=True)
    subtitle_path = Column(String(500), nullable=True)
    video_path = Column(String(500), nullable=True)
    timeline_path = Column(String(500), nullable=True)

    voice_settings = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "voice_id": "",
            "speed": 1.0,
            "pitch": 0.0,
            "sample_rate": 44100,
            "mock_mode": False,
        },
    )

    subtitle_settings = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "format": "srt",
            "max_words_per_line": 4,
            "highlight_color": "#F59E0B",
            "font_size": 42,
        },
    )

    quality_checks = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "audio_peak_db": -1.0,
            "duration_sync_delta": 0.0,
            "fps": 30,
            "passed": False,
            "production_eligible": False,
            "issues": [],
        },
    )

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    voice_tracks = relationship(
        "SceneVoiceTrack",
        back_populates="media_package",
        cascade="all, delete-orphan",
        order_by="SceneVoiceTrack.created_at",
    )


class SceneVoiceTrack(Base):
    """Represents an individual scene narration audio track with timing and waveform telemetry."""

    __tablename__ = "scene_voice_tracks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    media_package_id = Column(
        String(36),
        ForeignKey("media_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scene_id = Column(
        String(36),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    audio_path = Column(String(500), nullable=False)
    duration_sec = Column(Float, nullable=False, default=0.0)
    word_count = Column(Integer, nullable=False, default=0)
    waveform_peaks = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    media_package = relationship("MediaPackage", back_populates="voice_tracks")
    scene = relationship("Scene")
