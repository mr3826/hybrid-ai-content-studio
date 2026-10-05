from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
import yaml

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
        return EngineHealth(
            engine_id=self.id,
            status="healthy" if has_rules else "degraded",
            message=f"Media Engine active (FFmpeg: {'available' if has_ffmpeg else 'fallback deterministic mode'})",
            details={
                "has_rules": has_rules,
                "has_ffmpeg": has_ffmpeg,
                "ffmpeg_path": self.ffmpeg_adapter.ffmpeg_path,
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
        for s in scenes:
            track = self.audio_synthesizer.synthesize_scene_audio(
                scene_id=s.id,
                narration=s.narration,
                target_duration_sec=s.timing_estimate,
                config=cfg,
            )
            tracks.append(track)

        silence_gap = float(self.rules.get("voice", {}).get("silence_gap_sec", 0.15))
        master_path, total_duration = self.audio_synthesizer.stitch_master_audio(
            script_id=script_id,
            tracks=tracks,
            silence_gap_sec=silence_gap,
            sample_rate=cfg.sample_rate,
        )

        return VoiceSynthesisOutput(
            package_id=pkg_id,
            script_id=script_id,
            tracks=tracks,
            master_audio_path=master_path,
            total_duration_sec=total_duration,
        )

    def generate_subtitles(
        self,
        script_id: str,
        scenes: List[SceneMediaInput],
        track_durations: Optional[Dict[str, float]] = None,
        config: Optional[SubtitleConfigRequest] = None,
    ) -> SubtitleGenerationOutput:
        """Generates synchronized SRT/VTT timed captions."""
        return self.subtitle_adapter.generate_subtitles(
            script_id=script_id,
            scenes=scenes,
            track_durations=track_durations,
            config=config,
        )

    def render_media(
        self,
        script_id: str,
        package_id: str,
        scenes: List[SceneMediaInput],
        master_audio_path: str,
        total_duration_sec: float,
        config: Optional[MediaRenderConfigRequest] = None,
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

        # 1. Synthesize voice
        voice_out = self.synthesize_voice(script_id, scenes)

        # 2. Generate subtitles
        durations = {t.scene_id: t.duration_sec for t in voice_out.tracks}
        sub_out = self.generate_subtitles(script_id, scenes, track_durations=durations)

        # 3. Assemble video
        render_out = self.render_media(
            script_id=script_id,
            package_id=voice_out.package_id,
            scenes=scenes,
            master_audio_path=voice_out.master_audio_path,
            total_duration_sec=voice_out.total_duration_sec,
        )

        ended_at = datetime.now(timezone.utc)
        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            success=True,
            summary=f"Synthesized {len(voice_out.tracks)} voice tracks, {sub_out.cue_count} subtitle cues, and assembled {render_out.resolution} video.",
            outputs=[
                {
                    "package_id": voice_out.package_id,
                    "script_id": script_id,
                    "total_duration_sec": voice_out.total_duration_sec,
                    "audio_path": voice_out.master_audio_path,
                    "subtitle_path": sub_out.subtitle_path,
                    "video_path": render_out.video_path,
                    "quality_report": render_out.quality_report,
                }
            ],
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
            summary="Media Engine generates local narration WAVs, calculates sub-second subtitle cues, and stitches composition via FFmpeg.",
            factors=[
                {
                    "title": "Local Deterministic Synthesis",
                    "description": "100% offline PCM WAV generation with vocal harmonic modulation.",
                },
                {
                    "title": "Sub-second Subtitle Synchronization",
                    "description": "Word chunk pacing matches scene narration timestamps.",
                },
                {
                    "title": "FFmpeg Assembly",
                    "description": "Compiles visual assets + master audio into MP4 container.",
                },
            ],
        )
