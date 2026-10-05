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

    # SRT Format
    srt_out = adapter.generate_subtitles(
        script_id="script-sub-test",
        scenes=scenes,
        config=SubtitleConfigRequest(format="srt", max_words_per_line=3),
    )
    assert Path(srt_out.subtitle_path).exists()
    assert srt_out.cue_count >= 2
    assert "-->" in srt_out.content_text
    assert srt_out.cues[0].text in srt_out.content_text

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
