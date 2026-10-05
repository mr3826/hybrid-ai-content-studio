import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.engines.media.contracts import (
    MediaRenderConfigRequest,
    SceneMediaInput,
    SubtitleConfigRequest,
    SubtitleCueOutput,
    SubtitleGenerationOutput,
    VoiceConfigRequest,
    VoiceTrackOutput,
)
from app.engines.media.engine import MediaEngine
from app.models.media import MediaPackage, MediaPackageStatus, MediaResolution, SceneVoiceTrack
from app.models.scene import Scene
from app.models.script import ScriptDraft
from app.repositories.media_repository import MediaRepository
from app.repositories.scene_repository import SceneRepository

logger = logging.getLogger("studio.api.media")

router = APIRouter(prefix="/media", tags=["Media Engine"])
engine = MediaEngine()


# --- Pydantic Schemas ---

class SceneVoiceTrackResponse(BaseModel):
    id: str
    scene_id: str
    audio_path: str
    duration_sec: float
    word_count: int
    waveform_peaks: List[float]
    created_at: Any


class MediaPackageResponse(BaseModel):
    id: str
    script_id: str
    content_item_id: Optional[str] = None
    format: str
    resolution: str
    status: str
    total_duration_sec: float
    audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    timeline_path: Optional[str] = None
    voice_settings: Dict[str, Any]
    subtitle_settings: Dict[str, Any]
    quality_checks: Dict[str, Any]
    voice_tracks: List[SceneVoiceTrackResponse] = Field(default_factory=list)
    created_at: Any
    updated_at: Any


def _serialize_package(pkg: MediaPackage) -> Dict[str, Any]:
    tracks = []
    if pkg.voice_tracks:
        for t in pkg.voice_tracks:
            tracks.append({
                "id": t.id,
                "scene_id": t.scene_id,
                "audio_path": t.audio_path,
                "duration_sec": t.duration_sec,
                "word_count": t.word_count,
                "waveform_peaks": t.waveform_peaks or [],
                "created_at": t.created_at,
            })
    return {
        "id": pkg.id,
        "script_id": pkg.script_id,
        "content_item_id": pkg.content_item_id,
        "format": pkg.format,
        "resolution": pkg.resolution,
        "status": pkg.status,
        "total_duration_sec": pkg.total_duration_sec,
        "audio_path": pkg.audio_path,
        "subtitle_path": pkg.subtitle_path,
        "video_path": pkg.video_path,
        "timeline_path": pkg.timeline_path,
        "voice_settings": pkg.voice_settings or {},
        "subtitle_settings": pkg.subtitle_settings or {},
        "quality_checks": pkg.quality_checks or {},
        "voice_tracks": tracks,
        "created_at": pkg.created_at,
        "updated_at": pkg.updated_at,
    }


# --- Endpoints ---

@router.get("/voices")
async def list_available_voices():
    """List available voice profiles and presets."""
    return [
        {
            "id": "en-US-Studio-Standard",
            "name": "Standard Studio Narrator",
            "language": "en-US",
            "gender": "Neutral",
            "is_default": True,
        },
        {
            "id": "en-US-Studio-Authoritative",
            "name": "Authoritative Tech Benchmark",
            "language": "en-US",
            "gender": "Deep",
            "is_default": False,
        },
        {
            "id": "en-US-Studio-Casual",
            "name": "Casual Developer Demo",
            "language": "en-US",
            "gender": "Energetic",
            "is_default": False,
        },
        {
            "id": "bn-BD-Studio-Standard",
            "name": "Bangla Studio Narrator",
            "language": "bn-BD",
            "gender": "Neutral",
            "is_default": False,
        },
    ]


@router.get("/script/{script_id}", response_model=Optional[MediaPackageResponse])
async def get_media_package_for_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve active media package for a script."""
    repo = MediaRepository(db)
    pkg = await repo.get_package_by_script(script_id)
    if not pkg:
        return None
    return _serialize_package(pkg)


@router.post("/voice/{script_id}", response_model=MediaPackageResponse)
async def synthesize_script_voice(
    script_id: str,
    payload: Optional[VoiceConfigRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Synthesizes scene narration tracks and creates master narration audio."""
    config = payload or VoiceConfigRequest()
    scene_repo = SceneRepository(db)
    media_repo = MediaRepository(db)

    # 1. Fetch scenes
    scenes = await scene_repo.list_scenes_by_script(script_id)
    if not scenes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No storyboard scenes found for this script. Run decomposition first.",
        )

    # 2. Fetch or create MediaPackage
    pkg = await media_repo.get_package_by_script(script_id)
    if not pkg:
        # Get content_item_id from script
        script_res = await db.execute(select(ScriptDraft).where(ScriptDraft.id == script_id))
        script = script_res.scalar_one_or_none()
        content_item_id = script.content_item_id if script else None
        script_format = script.format if script else "short_vertical"

        pkg = MediaPackage(
            script_id=script_id,
            content_item_id=content_item_id,
            format=script_format,
            resolution=MediaResolution.VERTICAL_9_16 if "short" in script_format or "vertical" in script_format else MediaResolution.HORIZONTAL_16_9,
            status=MediaPackageStatus.SYNTHESIZING,
        )
        pkg = await media_repo.create_package(pkg)
    else:
        pkg.status = MediaPackageStatus.SYNTHESIZING
        await media_repo.update_package(pkg)

    # 3. Clear existing voice tracks for clean re-synthesis
    await media_repo.clear_voice_tracks(pkg.id)

    # 4. Synthesize voice tracks
    scenes_input = [
        SceneMediaInput(
            id=s.id,
            scene_order=s.scene_order,
            narration=s.narration,
            timing_estimate=s.timing_estimate,
            visual_type=s.visual_type,
            visual_source=s.visual_source,
            on_screen_text=s.on_screen_text,
        )
        for s in scenes
    ]

    out = engine.synthesize_voice(
        script_id=script_id,
        scenes=scenes_input,
        config=config,
        package_id=pkg.id,
    )

    # 5. Persist tracks
    for t in out.tracks:
        vt = SceneVoiceTrack(
            media_package_id=pkg.id,
            scene_id=t.scene_id,
            audio_path=t.audio_path,
            duration_sec=t.duration_sec,
            word_count=t.word_count,
            waveform_peaks=t.waveform_peaks,
        )
        await media_repo.add_voice_track(vt)

    # 6. Update package
    pkg.audio_path = out.master_audio_path
    pkg.total_duration_sec = out.total_duration_sec
    pkg.voice_settings = config.model_dump()
    pkg.status = MediaPackageStatus.READY
    await media_repo.update_package(pkg)

    refetched = await media_repo.get_package_by_id(pkg.id)
    return _serialize_package(refetched or pkg)


@router.post("/subtitles/{script_id}", response_model=SubtitleGenerationOutput)
async def generate_script_subtitles(
    script_id: str,
    payload: Optional[SubtitleConfigRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Generates synchronized timed captions (SRT / VTT)."""
    config = payload or SubtitleConfigRequest()
    scene_repo = SceneRepository(db)
    media_repo = MediaRepository(db)

    scenes = await scene_repo.list_scenes_by_script(script_id)
    if not scenes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No storyboard scenes found for this script.",
        )

    pkg = await media_repo.get_package_by_script(script_id)
    track_durations = {}
    if pkg and pkg.voice_tracks:
        track_durations = {t.scene_id: t.duration_sec for t in pkg.voice_tracks}

    scenes_input = [
        SceneMediaInput(
            id=s.id,
            scene_order=s.scene_order,
            narration=s.narration,
            timing_estimate=s.timing_estimate,
            visual_type=s.visual_type,
            visual_source=s.visual_source,
            on_screen_text=s.on_screen_text,
        )
        for s in scenes
    ]

    out = engine.generate_subtitles(
        script_id=script_id,
        scenes=scenes_input,
        track_durations=track_durations,
        config=config,
    )

    if pkg:
        pkg.subtitle_path = out.subtitle_path
        pkg.subtitle_settings = config.model_dump()
        await media_repo.update_package(pkg)

    return out


@router.get("/subtitles/{script_id}/file")
async def download_subtitles_file(
    script_id: str,
    format: str = Query("srt", pattern="^(srt|vtt)$"),
    db: AsyncSession = Depends(get_db),
):
    """Returns raw subtitle text stream."""
    media_repo = MediaRepository(db)
    pkg = await media_repo.get_package_by_script(script_id)
    if not pkg or not pkg.subtitle_path or not Path(pkg.subtitle_path).exists():
        raise HTTPException(status_code=404, detail="Subtitle file not found. Generate subtitles first.")

    with open(pkg.subtitle_path, "r", encoding="utf-8") as f:
        content = f.read()

    media_type = "text/vtt" if format == "vtt" else "application/x-subrip"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="subtitles_{script_id[:8]}.{format}"'},
    )


@router.post("/render/{script_id}", response_model=MediaPackageResponse)
async def render_script_media(
    script_id: str,
    payload: Optional[MediaRenderConfigRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Compiles scenes and master audio into a final video MP4."""
    config = payload or MediaRenderConfigRequest()
    scene_repo = SceneRepository(db)
    media_repo = MediaRepository(db)

    scenes = await scene_repo.list_scenes_by_script(script_id)
    if not scenes:
        raise HTTPException(status_code=400, detail="No storyboard scenes found.")

    pkg = await media_repo.get_package_by_script(script_id)
    if not pkg or not pkg.audio_path:
        # Auto-synthesize voice if not already present
        await synthesize_script_voice(script_id, None, db)
        pkg = await media_repo.get_package_by_script(script_id)

    pkg.status = MediaPackageStatus.RENDERING
    await media_repo.update_package(pkg)

    scenes_input = [
        SceneMediaInput(
            id=s.id,
            scene_order=s.scene_order,
            narration=s.narration,
            timing_estimate=s.timing_estimate,
            visual_type=s.visual_type,
            visual_source=s.visual_source,
            on_screen_text=s.on_screen_text,
        )
        for s in scenes
    ]

    out = engine.render_media(
        script_id=script_id,
        package_id=pkg.id,
        scenes=scenes_input,
        master_audio_path=pkg.audio_path,
        total_duration_sec=pkg.total_duration_sec,
        config=config,
    )

    pkg.video_path = out.video_path
    pkg.resolution = out.resolution
    pkg.quality_checks = out.quality_report
    pkg.status = MediaPackageStatus.READY
    await media_repo.update_package(pkg)

    refetched = await media_repo.get_package_by_id(pkg.id)
    return _serialize_package(refetched or pkg)
