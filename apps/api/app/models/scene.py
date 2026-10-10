import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VisualPriority:
    REAL_SCREEN_RECORDING = "real_screen_recording"
    BENCHMARK_CHART = "benchmark_chart"
    CODE_TERMINAL = "code_terminal"
    WORKFLOW_DIAGRAM = "workflow_diagram"
    PRODUCT_SCREENSHOT = "product_screenshot"
    ORIGINAL_MOTION_GRAPHIC = "original_motion_graphic"
    GENERATED_VISUAL = "generated_visual"

    ALL = [
        REAL_SCREEN_RECORDING,
        BENCHMARK_CHART,
        CODE_TERMINAL,
        WORKFLOW_DIAGRAM,
        PRODUCT_SCREENSHOT,
        ORIGINAL_MOTION_GRAPHIC,
        GENERATED_VISUAL,
    ]

    RANK_MAP = {
        REAL_SCREEN_RECORDING: 1,
        "screen_recording": 1,
        BENCHMARK_CHART: 2,
        "benchmark_chart": 2,
        "chart": 2,
        "benchmark": 2,
        CODE_TERMINAL: 3,
        "code_terminal": 3,
        "terminal": 3,
        "code": 3,
        WORKFLOW_DIAGRAM: 4,
        "workflow_diagram": 4,
        "diagram": 4,
        PRODUCT_SCREENSHOT: 5,
        "product_screenshot": 5,
        "screenshot": 5,
        "image": 5,
        ORIGINAL_MOTION_GRAPHIC: 6,
        "original_motion_graphic": 6,
        "motion_graphic": 6,
        GENERATED_VISUAL: 7,
        "generated_visual": 7,
        "generated": 7,
    }


class SceneStatus:
    DRAFT = "DRAFT"
    READY = "READY"
    MOCK = "MOCK"
    MISSING_ASSET = "MISSING_ASSET"
    RIGHTS_BLOCKED = "RIGHTS_BLOCKED"

    ALL = [DRAFT, READY, MOCK, MISSING_ASSET, RIGHTS_BLOCKED]


class TransitionType:
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    SLIDE_LEFT = "slide_left"
    WHIP_PAN = "whip_pan"
    ZOOM_IN = "zoom_in"

    ALL = [CUT, FADE, DISSOLVE, SLIDE_LEFT, WHIP_PAN, ZOOM_IN]


class Scene(Base, TimestampMixin):
    """Domain model representing a single storyboard scene inside Scene Studio."""
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    script_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("script_sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scene_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        index=True,
    )
    narration: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timing_estimate: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    on_screen_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_type: Mapped[str] = mapped_column(
        String(64),
        default=VisualPriority.REAL_SCREEN_RECORDING,
        nullable=False,
    )
    visual_source: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    asset_rights_record_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("asset_rights_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    transition: Mapped[str] = mapped_column(
        String(32),
        default=TransitionType.CUT,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=SceneStatus.DRAFT,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    script = relationship("ScriptDraft", lazy="select")
    section = relationship("ScriptSection", lazy="select")
    asset_rights = relationship("AssetRightsRecord", lazy="select")


class MediaAsset(Base, TimestampMixin):
    """Domain model representing a local or imported media asset with tagging and visual priority."""
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="image/png", nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), default="image", nullable=False)
    visual_priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    asset_rights_record_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("asset_rights_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    asset_rights = relationship("AssetRightsRecord", lazy="select")
