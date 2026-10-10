from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import yaml

from app.core.config import settings
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.media.adapters import (
    FFmpegMediaAdapter,
    LocalAudioSynthesizer,
    MediaPipelineError,
    SubtitleAdapter,
)
from app.engines.media.contracts import (
    MediaRenderConfigRequest,
    MediaRenderOutput,
    SceneMediaInput,
    SubtitleConfigRequest,
    SubtitleGenerationOutput,
    VoiceConfigRequest,
    VoiceSynthesisOutput,
)

logger = logging.getLogger("studio.engines.media")


class MediaEngine(BaseEngine):
    """Voice, Subtitle & Media Engine.
    Handles offline audio synthesis, synchronized timed captioning, and FFmpeg media timeline rendering.
    """

    id = "media"
    version = "1.0.0"

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)
        self.audio_synthesizer = LocalAudioSynthesizer()
        self.subtitle_adapter = SubtitleAdapter()
        self.ffmpeg_adapter = FFmpegMediaAdapter()

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError(f"MediaEngine rules could not be loaded from {self.engine_dir / 'rules.yaml'}")

    def health(self) -> EngineHealth:
        has_rules = bool(self.rules)
        has_ffmpeg = self.ffmpeg_adapter.has_ffmpeg()
        has_ffprobe = self.ffmpeg_adapter.has_ffprobe()
        voice_catalog = self.audio_synthesizer.get_voice_catalog()
        ready = has_rules and has_ffmpeg and has_ffprobe and bool(voice_catalog.get("available"))
        return EngineHealth(
            engine_id=self.id,
            status="healthy" if ready else "degraded",
            message=(
                "Media Engine production toolchain available."
                if ready
                else "Media Engine is missing one or more production tools; render/synthesis requests will fail closed."
            ),
            details={
                "has_rules": has_rules,
                "has_ffmpeg": has_ffmpeg,
                "has_ffprobe": has_ffprobe,
                "ffmpeg_path": self.ffmpeg_adapter.ffmpeg_path,
                "ffmpeg_version": self.ffmpeg_adapter.get_ffmpeg_version(),
                "ffprobe_path": self.ffmpeg_adapter.ffprobe_path,
                "ffprobe_version": self.ffmpeg_adapter.get_ffprobe_version(),
                "sapi5_available": bool(voice_catalog.get("available")),
                "sapi5_voices": voice_catalog.get("voices", []),
                "supported_languages": voice_catalog.get("supported_languages", []),
                "unavailable_languages": voice_catalog.get("unavailable_languages", []),
                "tts_mock_mode": settings.TTS_MOCK_MODE,
                "audio_dir": str(self.audio_synthesizer.output_dir),
                "subtitles_dir": str(self.subtitle_adapter.output_dir),
                "video_dir": str(self.ffmpeg_adapter.output_dir),
            },
        )

    def synthesize_voice(
        self,
        script_id: str,
        scenes: List[SceneMediaInput],
        config: Optional[VoiceConfigRequest] = None,
        package_id: Optional[str] = None,
    ) -> VoiceSynthesisOutput:
        """Synthesizes scene narration tracks and compiles master audio."""
        cfg = config or VoiceConfigRequest()
        pkg_id = package_id or str(uuid.uuid4())

        tracks = []
        for s in sorted(scenes, key=lambda scene: scene.scene_order):
            track = self.audio_synthesizer.synthesize_scene_audio(
                scene_id=s.id,
                narration=s.narration,
                target_duration_sec=s.timing_estimate,
                config=cfg,
            )
            tracks.append(track)

        silence_gap = float(self.rules.get("voice", {}).get("silence_gap_sec", 0.2))
        master_path, total_duration = self.audio_synthesizer.stitch_master_audio(
            script_id=script_id,
            tracks=tracks,
            silence_gap_sec=silence_gap,
            sample_rate=cfg.sample_rate,
        )
        if total_duration <= 0:
            raise MediaPipelineError("Narration synthesis produced an empty master audio track.", stage="voice")

        return VoiceSynthesisOutput(
            package_id=pkg_id,
            script_id=script_id,
            tracks=tracks,
            master_audio_path=master_path,
            total_duration_sec=total_duration,
            is_mock=any(track.is_mock for track in tracks),
        )

    def generate_subtitles(
        self,
        script_id: str,
        scenes: List[SceneMediaInput],
        track_durations: Optional[Dict[str, float]] = None,
        config: Optional[SubtitleConfigRequest] = None,
    ) -> SubtitleGenerationOutput:
        """Generates synchronized SRT/VTT timed captions."""
        silence_gap = float(self.rules.get("voice", {}).get("silence_gap_sec", 0.2))
        return self.subtitle_adapter.generate_subtitles(
            script_id=script_id,
            scenes=scenes,
            track_durations=track_durations,
            config=config,
            silence_gap_sec=silence_gap,
        )

    def render_media(
        self,
        script_id: str,
        package_id: str,
        scenes: List[SceneMediaInput],
        master_audio_path: str,
        total_duration_sec: float,
        config: Optional[MediaRenderConfigRequest] = None,
        subtitle_path: Optional[str] = None,
        audio_is_mock: bool = False,
        subtitle_timing_method: Optional[str] = None,
    ) -> MediaRenderOutput:
        """Assembles scenes and master audio into final video composition."""
        cfg = config or MediaRenderConfigRequest()
        return self.ffmpeg_adapter.assemble_media(
            script_id=script_id,
            package_id=package_id,
            scenes=scenes,
            master_audio_path=master_audio_path,
            total_duration_sec=total_duration_sec,
            config=cfg,
            subtitle_path=subtitle_path,
            audio_is_mock=audio_is_mock,
            subtitle_timing_method=subtitle_timing_method,
            silence_gap_sec=float(self.rules.get("voice", {}).get("silence_gap_sec", 0.2)),
        )

    async def run(self, context: EngineContext, session=None) -> EngineResult:
        """Executes full media workflow for a script storyboard."""
        started_at = datetime.now(timezone.utc)
        script_id = context.parameters.get("script_id")
        if not script_id:
            ended_at = datetime.now(timezone.utc)
            return EngineResult(
                engine_id=self.id,
                engine_version=self.version,
                run_id=context.run_id,
                started_at=started_at,
                ended_at=ended_at,
                success=False,
                summary="Missing required parameter: script_id",
            )

        scenes_raw = context.parameters.get("scenes", [])
        scenes = [SceneMediaInput(**s) if isinstance(s, dict) else s for s in scenes_raw]
        scenes.sort(key=lambda scene: scene.scene_order)

        if not scenes:
            ended_at = datetime.now(timezone.utc)
            return EngineResult(
                engine_id=self.id,
                engine_version=self.version,
                run_id=context.run_id,
                started_at=started_at,
                ended_at=ended_at,
                success=False,
                summary="No scenes provided for media synthesis",
            )

        parameters = context.parameters
        package_id = str(parameters.get("package_id") or uuid.uuid4())
        action = str(parameters.get("action", "render")).lower()
        if action not in {"synthesize", "render"}:
            return self._failure_result(context, started_at, f"Unsupported media action: {action}", package_id)

        try:
            voice_config = VoiceConfigRequest(**(parameters.get("voice_config") or {}))
            subtitle_config = SubtitleConfigRequest(**(parameters.get("subtitle_config") or {}))
            render_config = MediaRenderConfigRequest(**(parameters.get("render_config") or {}))
            master_audio_path = parameters.get("master_audio_path")
            voice_tracks: List[Dict[str, Any]] = []
            track_durations: Dict[str, float] = {
                str(scene_id): float(duration)
                for scene_id, duration in (parameters.get("voice_track_durations") or {}).items()
                if float(duration) > 0
            }
            audio_is_mock = bool(parameters.get("audio_is_mock", False))

            if action == "synthesize" or not master_audio_path:
                voice_out = self.synthesize_voice(
                    script_id=script_id,
                    scenes=scenes,
                    config=voice_config,
                    package_id=package_id,
                )
                master_audio_path = voice_out.master_audio_path
                track_durations = {track.scene_id: track.duration_sec for track in voice_out.tracks}
                voice_tracks = [track.model_dump(mode="json") for track in voice_out.tracks]
                audio_is_mock = voice_out.is_mock
                total_duration = voice_out.total_duration_sec
            else:
                total_duration = float(parameters.get("total_duration_sec") or 0.0)

            for scene in scenes:
                if scene.id in track_durations:
                    scene.actual_audio_duration_sec = track_durations[scene.id]

            if action == "synthesize":
                ended_at = datetime.now(timezone.utc)
                mock_status = audio_is_mock
                output = {
                    "package_id": package_id,
                    "script_id": script_id,
                    "status": "MOCK" if mock_status else "SYNTHESIZED",
                    "total_duration_sec": total_duration,
                    "audio_path": master_audio_path,
                    "voice_tracks": voice_tracks,
                    "audio_is_mock": audio_is_mock,
                    "quality_report": {"passed": False, "production_eligible": False, "issues": ["Video render has not been completed."]},
                }
                return EngineResult(
                    engine_id=self.id,
                    engine_version=self.version,
                    run_id=context.run_id,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                    success=not mock_status,
                    summary="Mock narration generated for isolated testing; not production-ready." if mock_status else f"Generated {len(voice_tracks)} offline SAPI5 narration tracks.",
                    outputs=[output],
                    errors=["Mock narration cannot be marked production-ready."] if mock_status else [],
                )

            if render_config.burn_subtitles:
                subtitle_path = parameters.get("subtitle_path")
                if subtitle_path:
                    subtitle_timing_method = str(parameters.get("subtitle_timing_method") or "not_applicable")
                else:
                    sub_out = self.generate_subtitles(
                        script_id=script_id,
                        scenes=scenes,
                        track_durations=track_durations,
                        config=subtitle_config,
                    )
                    subtitle_path = sub_out.subtitle_path
                    subtitle_timing_method = sub_out.timing_method
            else:
                subtitle_path = None
                subtitle_timing_method = None

            render_out = self.render_media(
                script_id=script_id,
                package_id=package_id,
                scenes=scenes,
                master_audio_path=str(master_audio_path),
                total_duration_sec=total_duration,
                config=render_config,
                subtitle_path=subtitle_path,
                audio_is_mock=audio_is_mock,
                subtitle_timing_method=subtitle_timing_method,
            )
            output = {
                "package_id": package_id,
                "script_id": script_id,
                "status": render_out.status,
                "total_duration_sec": render_out.duration_sec,
                "audio_path": master_audio_path,
                "voice_tracks": voice_tracks,
                "audio_is_mock": audio_is_mock,
                "subtitle_path": subtitle_path,
                "subtitle_timing_method": subtitle_timing_method,
                "video_path": render_out.video_path,
                "timeline_path": render_out.timeline_path,
                "quality_report": render_out.quality_report,
            }
            ended_at = datetime.now(timezone.utc)
            production_ready = render_out.quality_report.get("passed") is True and render_out.status == "READY"
            return EngineResult(
                engine_id=self.id,
                engine_version=self.version,
                run_id=context.run_id,
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                success=production_ready,
                summary=(
                    f"Rendered verified {render_out.resolution} media."
                    if production_ready
                    else "A valid mock media artifact was rendered for isolated testing; it is not production-ready."
                ),
                outputs=[output],
                errors=[] if production_ready else list(render_out.quality_report.get("issues", [])),
            )
        except MediaPipelineError as exc:
            return self._failure_result(context, started_at, str(exc), package_id, failed_stage=exc.stage)
        except Exception as exc:
            logger.exception("Unexpected media engine failure for script %s", script_id)
            return self._failure_result(context, started_at, f"Media pipeline failed: {exc}", package_id)

    def _failure_result(
        self,
        context: EngineContext,
        started_at: datetime,
        message: str,
        package_id: str,
        failed_stage: str = "media",
    ) -> EngineResult:
        ended_at = datetime.now(timezone.utc)
        output = {
            "package_id": package_id,
            "status": "FAILED",
            "quality_report": {
                "passed": False,
                "production_eligible": False,
                "failed_stage": failed_stage,
                "issues": [message],
            },
        }
        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            success=False,
            summary=message,
            outputs=[output],
            errors=[message],
        )

    async def dry_run(self, context: EngineContext, session=None) -> EngineResult:
        """Simulates media synthesis and checks toolchain without writing files."""
        started_at = datetime.now(timezone.utc)
        script_id = context.parameters.get("script_id", "sim-script")
        scenes_count = len(context.parameters.get("scenes", []))
        ended_at = datetime.now(timezone.utc)
        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            success=True,
            summary=f"[Dry-Run] Media engine simulation for script {script_id} with {scenes_count} scenes.",
            outputs=[
                {
                    "ffmpeg_available": self.ffmpeg_adapter.has_ffmpeg(),
                    "simulated_duration_sec": scenes_count * 3.0,
                    "resolution": "1080x1920",
                }
            ],
        )

    def explain(self, result_id: str) -> EngineExplanation:
        """Provides human-readable explanation of media engine operation."""
        return EngineExplanation(
            result_id=result_id,
            summary="Media Engine uses installed offline SAPI5 voices, measured scene timing, local assets, FFmpeg, and FFprobe verification.",
            factors=[
                {
                    "title": "Offline System Speech",
                    "description": "Uses an installed Windows SAPI5 voice; harmonic audio is labeled mock and cannot pass production QC.",
                },
                {
                    "title": "Measured Subtitle Timing",
                    "description": "Scene boundaries use measured narration durations and configured silence gaps; word-level cue timing is a proportional estimate.",
                },
                {
                    "title": "FFmpeg Assembly",
                    "description": "Composes each ordered scene asset, retains aspect ratio, burns required captions, and verifies codecs/streams/durations with FFprobe.",
                },
            ],
        )
