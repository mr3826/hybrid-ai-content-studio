from pathlib import Path
import wave
import pytest

from app.engines.core.base import EngineContext
from app.engines.media.adapters import (
    FFmpegMediaAdapter,
    LocalAudioSynthesizer,
    SubtitleAdapter,
)
from app.engines.media.contracts import (
    MediaRenderConfigRequest,
    SceneMediaInput,
    SubtitleConfigRequest,
    VoiceConfigRequest,
)
from app.engines.media.engine import MediaEngine


def test_media_engine_manifest_and_health():
    engine = MediaEngine()
    engine.validate_config()
    health = engine.health()

    assert health.status in ("healthy", "degraded")
    assert "details" in health.model_dump()
    assert health.details["has_rules"] is True
    assert "tts_mock_mode" in health.details
    assert "ffmpeg_version" in health.details


def test_local_audio_synthesis_and_master_stitch(tmp_path):
    synthesizer = LocalAudioSynthesizer(output_dir=str(tmp_path / "audio"))

    # Synthesize scene 1 audio
    track1 = synthesizer.synthesize_scene_audio(
        scene_id="scene-test-1",
        narration="Testing the local audio synthesizer with speech cadence modulation.",
        target_duration_sec=3.0,
        config=VoiceConfigRequest(voice_id="en-US-Studio-Standard", speed=1.0),
    )
    assert Path(track1.audio_path).exists()
    assert track1.duration_sec >= 1.0
    assert len(track1.waveform_peaks) == 50
    assert all(0.0 <= p <= 1.0 for p in track1.waveform_peaks)

    # Verify WAV header
    with wave.open(track1.audio_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 44100
        assert wf.getnframes() > 0

    # Synthesize scene 2 audio
    track2 = synthesizer.synthesize_scene_audio(
        scene_id="scene-test-2",
        narration="Second scene benchmark verification complete.",
        target_duration_sec=2.0,
        config=VoiceConfigRequest(voice_id="en-US-Studio-Standard", speed=1.0),
    )

    # Stitch master audio
    master_path, master_dur = synthesizer.stitch_master_audio(
        script_id="script-test-123",
        tracks=[track1, track2],
        silence_gap_sec=0.2,
    )
    assert Path(master_path).exists()
    assert master_dur >= track1.duration_sec + track2.duration_sec

    # Measure audio peak dB
    peak_db = LocalAudioSynthesizer.get_audio_peak_db(master_path)
    assert -60.0 <= peak_db <= 0.0


def test_voice_profiles_and_tts_mode_toggle(tmp_path):
    synthesizer = LocalAudioSynthesizer(output_dir=str(tmp_path / "audio"))

    profiles = [
        "en-US-Studio-Standard",
        "en-US-Studio-Authoritative",
        "en-US-Studio-Casual",
        "bn-BD-Studio-Standard",
    ]

    for p in profiles:
        track = synthesizer.synthesize_scene_audio(
            scene_id=f"scene-{p}",
            narration="Distinct vocal profile testing with acoustic modulation.",
            target_duration_sec=2.0,
            config=VoiceConfigRequest(voice_id=p, speed=1.1, mock_mode=True),
        )
        assert Path(track.audio_path).exists()
        assert track.duration_sec > 0.5
        assert len(track.waveform_peaks) == 50

    # Verify mock_mode=False either returns system TTS or gracefully falls back
    fallback_track = synthesizer.synthesize_scene_audio(
        scene_id="scene-offline-live",
        narration="Offline speech fallback verification.",
        target_duration_sec=2.0,
        config=VoiceConfigRequest(mock_mode=False),
    )
    assert Path(fallback_track.audio_path).exists()
    assert fallback_track.duration_sec > 0.5


def test_subtitle_generation_srt_and_vtt(tmp_path):
    adapter = SubtitleAdapter(output_dir=str(tmp_path / "subtitles"))

    scenes = [
        SceneMediaInput(
            id="s1",
            scene_order=1,
            narration="Watch our local coding assistant run offline.",
            timing_estimate=3.0,
        ),
        SceneMediaInput(
            id="s2",
            scene_order=2,
            narration="We measured 142 tokens per second on RTX 4090.",
            timing_estimate=3.5,
        ),
    ]

    # SRT Format with pacing metrics and silence gap synchronization
    srt_out = adapter.generate_subtitles(
        script_id="script-sub-test",
        scenes=scenes,
        config=SubtitleConfigRequest(format="srt", max_words_per_line=3, silence_gap_sec=0.2),
    )
    assert Path(srt_out.subtitle_path).exists()
    assert srt_out.cue_count >= 2
    assert "-->" in srt_out.content_text
    assert srt_out.cues[0].text in srt_out.content_text
    assert srt_out.avg_cps > 0
    assert srt_out.pacing_status in ("OPTIMAL", "FAST", "SLOW")

    # Verify cue 1 start is 0.0 and subsequent scene start accounts for silence gap
    assert srt_out.cues[0].start_sec == 0.0
    scene2_cues = [c for c in srt_out.cues if c.scene_id == "s2"]
    if scene2_cues:
        scene1_end = max(c.end_sec for c in srt_out.cues if c.scene_id == "s1")
        assert scene2_cues[0].start_sec >= scene1_end

    # VTT Format
    vtt_out = adapter.generate_subtitles(
        script_id="script-sub-test-2",
        scenes=scenes,
        config=SubtitleConfigRequest(format="vtt", max_words_per_line=4),
    )
    assert Path(vtt_out.subtitle_path).exists()
    assert vtt_out.content_text.startswith("WEBVTT")


def test_media_assembly_and_timeline(tmp_path):
    synthesizer = LocalAudioSynthesizer(output_dir=str(tmp_path / "audio"))
    ffmpeg_adapter = FFmpegMediaAdapter(output_dir=str(tmp_path / "video"))

    track = synthesizer.synthesize_scene_audio(
        scene_id="s1",
        narration="Media assembly test scene narration.",
        target_duration_sec=2.0,
        config=VoiceConfigRequest(),
    )

    scenes = [
        SceneMediaInput(
            id="s1",
            scene_order=1,
            narration="Media assembly test scene narration.",
            timing_estimate=2.0,
            visual_type="real_screen_recording",
        )
    ]

    render_out = ffmpeg_adapter.assemble_media(
        script_id="script-render-1",
        package_id="pkg-render-1",
        scenes=scenes,
        master_audio_path=track.audio_path,
        total_duration_sec=track.duration_sec,
        config=MediaRenderConfigRequest(resolution="1080x1920", fps=30),
    )

    assert Path(render_out.video_path).exists()
    assert render_out.status == "READY"
    assert render_out.resolution == "1080x1920"
    assert render_out.file_size_bytes > 0
    assert render_out.quality_report["passed"] is True
    assert render_out.quality_report["duration_sync_delta"] <= 0.25


def test_media_resolution_normalization_and_subtitle_burn(tmp_path):
    synthesizer = LocalAudioSynthesizer(output_dir=str(tmp_path / "audio"))
    sub_adapter = SubtitleAdapter(output_dir=str(tmp_path / "subtitles"))
    ffmpeg_adapter = FFmpegMediaAdapter(output_dir=str(tmp_path / "video"))

    track = synthesizer.synthesize_scene_audio(
        scene_id="s1",
        narration="Testing subtitle burn-in with horizontal aspect ratio.",
        target_duration_sec=2.0,
        config=VoiceConfigRequest(),
    )

    scenes = [
        SceneMediaInput(
            id="s1",
            scene_order=1,
            narration="Testing subtitle burn-in with horizontal aspect ratio.",
            timing_estimate=2.0,
        )
    ]

    sub_out = sub_adapter.generate_subtitles(
        script_id="script-burn-1",
        scenes=scenes,
    )

    # Render horizontal with burn_subtitles=True
    render_out = ffmpeg_adapter.assemble_media(
        script_id="script-burn-1",
        package_id="pkg-burn-1",
        scenes=scenes,
        master_audio_path=track.audio_path,
        total_duration_sec=track.duration_sec,
        config=MediaRenderConfigRequest(resolution="horizontal_16_9", fps=30, burn_subtitles=True),
        subtitle_path=sub_out.subtitle_path,
    )

    assert Path(render_out.video_path).exists()
    assert render_out.resolution == "1920x1080"
    assert render_out.quality_report["width"] == 1920
    assert render_out.quality_report["height"] == 1080
    assert "audio_peak_db" in render_out.quality_report


def test_ffmpeg_deterministic_fallback_when_binary_missing(tmp_path):
    ffmpeg_adapter = FFmpegMediaAdapter(output_dir=str(tmp_path / "video"))
    ffmpeg_adapter.ffmpeg_path = None  # Simulate missing binary

    scenes = [
        SceneMediaInput(
            id="s1",
            scene_order=1,
            narration="Testing fallback mode without FFmpeg binary.",
            timing_estimate=2.0,
        )
    ]

    render_out = ffmpeg_adapter.assemble_media(
        script_id="script-fallback-1",
        package_id="pkg-fallback-1",
        scenes=scenes,
        master_audio_path="data/assets/audio/nonexistent.wav",
        total_duration_sec=2.0,
        config=MediaRenderConfigRequest(resolution="vertical_9_16"),
    )

    assert Path(render_out.video_path).exists()
    assert render_out.status == "READY"
    assert render_out.quality_report["ffmpeg_available"] is False
    assert render_out.quality_report["passed"] is True
    assert render_out.resolution == "1080x1920"


@pytest.mark.asyncio
async def test_media_engine_run_and_explain(tmp_path):
    engine = MediaEngine()
    engine.audio_synthesizer.output_dir = tmp_path / "audio"
    engine.audio_synthesizer.output_dir.mkdir(parents=True, exist_ok=True)
    engine.subtitle_adapter.output_dir = tmp_path / "subtitles"
    engine.subtitle_adapter.output_dir.mkdir(parents=True, exist_ok=True)
    engine.ffmpeg_adapter.output_dir = tmp_path / "video"
    engine.ffmpeg_adapter.output_dir.mkdir(parents=True, exist_ok=True)

    ctx = EngineContext(
        run_id="run-media-1",
        parameters={
            "script_id": "script-e2e-1",
            "scenes": [
                {
                    "id": "s1",
                    "scene_order": 1,
                    "narration": "First scene test narration.",
                    "timing_estimate": 2.5,
                },
                {
                    "id": "s2",
                    "scene_order": 2,
                    "narration": "Second scene test narration with metrics.",
                    "timing_estimate": 3.0,
                },
            ],
        },
    )

    res = await engine.run(ctx)
    assert res.success is True
    assert len(res.outputs) == 1
    out = res.outputs[0]
    assert "package_id" in out
    assert Path(out["audio_path"]).exists()
    assert Path(out["subtitle_path"]).exists()
    assert Path(out["video_path"]).exists()

    explanation = engine.explain(out["package_id"])
    assert explanation.result_id == out["package_id"]
    assert len(explanation.factors) >= 3
