import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
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
from app.engines.media.adapters import (
    AssetUnavailableError,
    MediaPipelineError,
    TTSUnavailableError,
    UnsupportedVoiceError,
)
from app.engines.media.engine import MediaEngine
from app.models.media import MediaPackage, MediaPackageStatus, MediaResolution, SceneVoiceTrack
from app.models.scene import Scene, SceneStatus
from app.models.script import ScriptDraft
from app.repositories.media_repository import MediaRepository
from app.repositories.scene_repository import SceneRepository
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobRead

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
    is_mock: bool
    synthesis_mode: Literal["windows_sapi5", "mock_harmonic"]
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
    quality_report: Optional[Dict[str, Any]] = None
    voice_tracks: List[SceneVoiceTrackResponse] = Field(default_factory=list)
    created_at: Any
    updated_at: Any


class MediaJobRequest(BaseModel):
    action: Literal["synthesize", "render"] = "render"
    voice_config: VoiceConfigRequest = Field(default_factory=VoiceConfigRequest)
    subtitle_config: SubtitleConfigRequest = Field(default_factory=SubtitleConfigRequest)
    render_config: MediaRenderConfigRequest = Field(
        default_factory=lambda: MediaRenderConfigRequest(burn_subtitles=True)
    )


def _build_scene_inputs(
    scenes: List[Scene],
    track_durations: Optional[Dict[str, float]] = None,
) -> List[SceneMediaInput]:
    durations = track_durations or {}
    return [
        SceneMediaInput(
            id=scene.id,
            scene_order=scene.scene_order,
            narration=scene.narration,
            timing_estimate=scene.timing_estimate,
            visual_type=scene.visual_type,
            visual_source=scene.visual_source,
            visual_is_mock=scene.status == SceneStatus.MOCK,
            actual_audio_duration_sec=durations.get(scene.id),
            on_screen_text=scene.on_screen_text,
        )
        for scene in sorted(scenes, key=lambda item: item.scene_order)
    ]


def _pipeline_error_status(error: MediaPipelineError) -> int:
    if isinstance(error, (UnsupportedVoiceError, AssetUnavailableError)) or error.stage in {
        "configuration", "timeline", "subtitles", "svg_rasterization"
    }:
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    if isinstance(error, TTSUnavailableError) or error.stage in {"voice", "render", "verification"}:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _mark_failed_package(pkg: MediaPackage, error: MediaPipelineError) -> None:
    pkg.status = MediaPackageStatus.FAILED
    pkg.audio_path = None if error.stage == "voice" else pkg.audio_path
    pkg.video_path = None
    pkg.timeline_path = None
    pkg.quality_checks = {
        "passed": False,
        "production_eligible": False,
        "failed_stage": error.stage,
        "issues": [str(error)],
    }


def _serialize_package(pkg: MediaPackage) -> Dict[str, Any]:
    tracks = []
    resolved_mock_mode = (pkg.voice_settings or {}).get("resolved_mock_mode")
    if pkg.voice_tracks:
        for t in pkg.voice_tracks:
            tracks.append({
                "id": t.id,
                "scene_id": t.scene_id,
                "audio_path": t.audio_path,
                "duration_sec": t.duration_sec,
                "word_count": t.word_count,
                "waveform_peaks": t.waveform_peaks or [],
                "is_mock": resolved_mock_mode is not False,
                "synthesis_mode": "mock_harmonic" if resolved_mock_mode is not False else "windows_sapi5",
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
        "quality_report": pkg.quality_checks or {},
        "voice_tracks": tracks,
        "created_at": pkg.created_at,
        "updated_at": pkg.updated_at,
    }


# --- Endpoints ---

@router.get("/voices")
async def list_available_voices():
    """Expose actual enabled SAPI5 voices and installed language support."""
    return engine.audio_synthesizer.get_voice_catalog()


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
    scenes_input = _build_scene_inputs(scenes)

    try:
        out = engine.synthesize_voice(
            script_id=script_id,
            scenes=scenes_input,
            config=config,
            package_id=pkg.id,
        )
    except MediaPipelineError as exc:
        _mark_failed_package(pkg, exc)
        await media_repo.update_package(pkg)
        raise HTTPException(status_code=_pipeline_error_status(exc), detail=str(exc)) from exc

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
    pkg.voice_settings = {
        **config.model_dump(),
        "resolved_mock_mode": out.is_mock,
        "synthesis_modes": sorted({track.synthesis_mode for track in out.tracks}),
    }
    pkg.video_path = None
    pkg.timeline_path = None
    pkg.quality_checks = {
        "passed": False,
        "production_eligible": False,
        "issues": ["Final video render has not been completed."],
    }
    pkg.status = MediaPackageStatus.MOCK if out.is_mock else MediaPackageStatus.SYNTHESIZED
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

    scenes_input = _build_scene_inputs(scenes, track_durations)

    out = engine.generate_subtitles(
        script_id=script_id,
        scenes=scenes_input,
        track_durations=track_durations,
        config=config,
    )

    if pkg:
        pkg.subtitle_path = out.subtitle_path
        pkg.subtitle_settings = {
            **config.model_dump(),
            "timing_method": out.timing_method,
            "timing_limitation": out.timing_limitation,
        }
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
    if not pkg or not pkg.subtitle_path:
        raise HTTPException(status_code=404, detail="Subtitle file not found. Generate subtitles first.")

    subtitle_path = Path(pkg.subtitle_path)
    if not subtitle_path.is_absolute():
        subtitle_path = subtitle_path if subtitle_path.exists() else Path("data/assets/subtitles") / subtitle_path
    try:
        subtitle_path = subtitle_path.resolve(strict=True)
        subtitle_path.relative_to(Path("data/assets/subtitles").resolve())
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(status_code=404, detail="Subtitle file not found in the local subtitle asset directory.")
    if not subtitle_path.is_file():
        raise HTTPException(status_code=404, detail="Subtitle file not found. Generate subtitles first.")

    with open(subtitle_path, "r", encoding="utf-8") as f:
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

    # Auto-generate subtitles if burn_subtitles requested and not yet generated
    if config.burn_subtitles:
        if not pkg.subtitle_path or not Path(pkg.subtitle_path).exists():
            sub_res = await generate_script_subtitles(script_id, None, db)
            pkg.subtitle_path = sub_res.subtitle_path

    pkg.status = MediaPackageStatus.RENDERING
    await media_repo.update_package(pkg)

    track_durations = {track.scene_id: track.duration_sec for track in pkg.voice_tracks or []}
    scenes_input = _build_scene_inputs(scenes, track_durations)

    # Older packages have no synthesis provenance. Treat them as non-production until re-synthesized.
    audio_is_mock = (pkg.voice_settings or {}).get("resolved_mock_mode") is not False
    try:
        out = engine.render_media(
            script_id=script_id,
            package_id=pkg.id,
            scenes=scenes_input,
            master_audio_path=pkg.audio_path,
            total_duration_sec=pkg.total_duration_sec,
            config=config,
            subtitle_path=pkg.subtitle_path if config.burn_subtitles else None,
            audio_is_mock=audio_is_mock,
            subtitle_timing_method=(pkg.subtitle_settings or {}).get("timing_method"),
        )
    except MediaPipelineError as exc:
        _mark_failed_package(pkg, exc)
        await media_repo.update_package(pkg)
        raise HTTPException(status_code=_pipeline_error_status(exc), detail=str(exc)) from exc

    pkg.video_path = out.video_path
    pkg.timeline_path = out.timeline_path
    pkg.resolution = out.resolution
    pkg.total_duration_sec = out.duration_sec
    pkg.quality_checks = out.quality_report
    pkg.status = out.status
    await media_repo.update_package(pkg)

    refetched = await media_repo.get_package_by_id(pkg.id)
    return _serialize_package(refetched or pkg)


@router.post("/jobs/{script_id}", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_media_job(
    script_id: str,
    payload: MediaJobRequest,
    db: AsyncSession = Depends(get_db),
):
    """Queue production synthesis/render work for the local Python media worker."""
    scene_repo = SceneRepository(db)
    media_repo = MediaRepository(db)
    scenes = await scene_repo.list_scenes_by_script(script_id)
    if not scenes:
        raise HTTPException(status_code=400, detail="No storyboard scenes found.")

    script_res = await db.execute(select(ScriptDraft).where(ScriptDraft.id == script_id))
    script = script_res.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found.")

    pkg = await media_repo.get_package_by_script(script_id)
    if not pkg:
        pkg = MediaPackage(
            script_id=script_id,
            content_item_id=script.content_item_id,
            format=script.format,
            resolution=(
                MediaResolution.VERTICAL_9_16
                if "short" in script.format or "vertical" in script.format
                else MediaResolution.HORIZONTAL_16_9
            ),
            status=MediaPackageStatus.DRAFT,
        )
        pkg = await media_repo.create_package(pkg)

    needs_synthesis = payload.action == "synthesize" or not pkg.audio_path
    if needs_synthesis:
        await media_repo.clear_voice_tracks(pkg.id)
        pkg.audio_path = None
        pkg.total_duration_sec = 0.0
        pkg.subtitle_path = None
        pkg.voice_settings = payload.voice_config.model_dump()
        pkg.status = MediaPackageStatus.SYNTHESIZING
    else:
        pkg.status = MediaPackageStatus.RENDERING
    pkg.video_path = None
    pkg.timeline_path = None
    pkg.quality_checks = {
        "passed": False,
        "production_eligible": False,
        "issues": ["Media worker job is pending."],
    }
    await media_repo.update_package(pkg)

    track_durations = (
        {}
        if needs_synthesis
        else {track.scene_id: track.duration_sec for track in pkg.voice_tracks or []}
    )
    scenes_input = _build_scene_inputs(scenes, track_durations)
    parameters: Dict[str, Any] = {
        "script_id": script_id,
        "package_id": pkg.id,
        "action": payload.action,
        "scenes": [scene.model_dump(exclude_none=True) for scene in scenes_input],
        "voice_config": payload.voice_config.model_dump(),
        "subtitle_config": payload.subtitle_config.model_dump(),
        "render_config": payload.render_config.model_dump(),
    }
    if not needs_synthesis:
        parameters.update({
            "master_audio_path": pkg.audio_path,
            "total_duration_sec": pkg.total_duration_sec,
            "voice_track_durations": track_durations,
            # Missing provenance on legacy packages fails closed as mock.
            "audio_is_mock": (pkg.voice_settings or {}).get("resolved_mock_mode") is not False,
            "subtitle_path": pkg.subtitle_path if payload.render_config.burn_subtitles else None,
            "subtitle_timing_method": (pkg.subtitle_settings or {}).get("timing_method"),
        })

    job_repo = JobRepository(db)
    job = await job_repo.create_job(
        job_type="engine_run",
        engine_id="media",
        project_id=script.content_item_id,
        payload={"dry_run": False, "parameters": parameters},
    )
    return job
