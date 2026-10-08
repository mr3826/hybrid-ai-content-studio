from pathlib import Path
import binascii
import math
import struct
import subprocess
import wave
import zlib

import pytest

from app.engines.media.adapters import (
    AssetUnavailableError,
    FFmpegMediaAdapter,
    LocalAudioSynthesizer,
    MediaPipelineError,
    MediaRenderError,
    SubtitleAdapter,
    TTSUnavailableError,
    UnsupportedVoiceError,
)
from app.engines.media.contracts import (
    MediaRenderConfigRequest,
    SceneMediaInput,
    SubtitleConfigRequest,
    VoiceConfigRequest,
)
from app.engines.media.engine import MediaEngine


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _write_png(path: Path, color: tuple[int, int, int], width: int = 96, height: int = 72) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    scanline = b"\x00" + bytes(color) * width
    pixels = scanline * height
    header = struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(pixels))
        + _png_chunk(b"IEND", b"")
    )
    return path


def _write_wav(path: Path, duration: float = 0.8, sample_rate: int = 44100) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = round(duration * sample_rate)
    samples = [int(10000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(frame_count)]
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as source:
        return source.getnframes() / source.getframerate()


def _adapter(tmp_path: Path) -> FFmpegMediaAdapter:
    root = tmp_path / "assets"
    root.mkdir(parents=True, exist_ok=True)
    return FFmpegMediaAdapter(output_dir=str(tmp_path / "video"), asset_root=str(root))


def _require_local_ffmpeg(adapter: FFmpegMediaAdapter) -> None:
    if not adapter.has_ffmpeg() or not adapter.has_ffprobe():
        pytest.skip("This regression requires the locally installed FFmpeg and FFprobe binaries.")


def _render(adapter: FFmpegMediaAdapter, script: str, package: str, audio: Path, image: Path, *, resolution="vertical_9_16", subtitles=None):
    duration = _wav_duration(audio)
    scene = SceneMediaInput(
        id=f"scene-{package}",
        scene_order=1,
        narration="This visual belongs to this topic.",
        timing_estimate=duration,
        visual_type="product_screenshot",
        visual_source=str(image),
        actual_audio_duration_sec=duration,
    )
    return adapter.assemble_media(
        script_id=script,
        package_id=package,
        scenes=[scene],
        master_audio_path=str(audio),
        total_duration_sec=duration,
        config=MediaRenderConfigRequest(
            resolution=resolution,
            fps=30,
            burn_subtitles=subtitles is not None,
        ),
        subtitle_path=str(subtitles) if subtitles else None,
        audio_is_mock=True,
        subtitle_timing_method="proportional_to_measured_scene_audio",
    )


def test_mock_harmonic_audio_is_explicit_and_marked(tmp_path):
    synthesizer = LocalAudioSynthesizer(output_dir=str(tmp_path / "audio"))
    track = synthesizer.synthesize_scene_audio(
        scene_id="mock-scene",
        narration="This is a test fixture, not spoken narration.",
        target_duration_sec=0.8,
        config=VoiceConfigRequest(voice_id="test-only", mock_mode=True),
    )

    assert Path(track.audio_path).is_file()
    assert track.is_mock is True
    assert track.synthesis_mode == "mock_harmonic"


def test_real_tts_unavailable_fails_without_harmonic_fallback(tmp_path):
    synthesizer = LocalAudioSynthesizer(output_dir=str(tmp_path / "audio"))
    synthesizer._voice_catalog = {
        "available": False,
        "default_voice_id": None,
        "voices": [],
        "supported_languages": [],
        "unavailable_languages": ["en-US", "bn-BD"],
        "message": "No enabled system voices.",
    }

    with pytest.raises(TTSUnavailableError, match="No enabled system voices"):
        synthesizer.synthesize_scene_audio(
            scene_id="production-scene",
            narration="Must be spoken by a real installed voice.",
            target_duration_sec=2.0,
            config=VoiceConfigRequest(mock_mode=False),
        )
    assert not list((tmp_path / "audio").glob("*.wav"))


def test_unsupported_voice_reports_installed_languages(tmp_path):
    synthesizer = LocalAudioSynthesizer(output_dir=str(tmp_path / "audio"))
    synthesizer._voice_catalog = {
        "available": True,
        "default_voice_id": "English Voice",
        "voices": [{"id": "English Voice", "name": "English Voice", "locale": "en-US", "gender": "Female"}],
        "supported_languages": ["en-US"],
        "unavailable_languages": ["bn-BD"],
        "message": "",
    }

    with pytest.raises(UnsupportedVoiceError, match="bn-BD is unsupported"):
        synthesizer.synthesize_scene_audio(
            scene_id="unsupported-scene",
            narration="Unsupported language request.",
            target_duration_sec=2.0,
            config=VoiceConfigRequest(voice_id="bn-BD-Studio-Standard", mock_mode=False),
        )
    assert not list((tmp_path / "audio").glob("*.wav"))


def test_missing_ffmpeg_fails_without_creating_fake_mp4(tmp_path):
    adapter = _adapter(tmp_path)
    adapter.ffmpeg_path = None
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")

    with pytest.raises(MediaRenderError, match="FFmpeg is not installed"):
        adapter.assemble_media(
            script_id="missing-ffmpeg",
            package_id="missing-ffmpeg",
            scenes=[SceneMediaInput(id="s1", scene_order=1, narration="No render.", timing_estimate=0.8)],
            master_audio_path=str(audio),
            total_duration_sec=0.8,
            config=MediaRenderConfigRequest(burn_subtitles=False),
        )
    assert not list((tmp_path / "video").glob("*.mp4"))


def test_missing_scene_asset_and_asset_escape_fail_closed(tmp_path):
    adapter = _adapter(tmp_path)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    scene = SceneMediaInput(id="s1", scene_order=1, narration="Needs a real visual.", timing_estimate=0.8)

    with pytest.raises(AssetUnavailableError, match="asset before rendering"):
        adapter.assemble_media("no-asset", "no-asset", [scene], str(audio), 0.8, MediaRenderConfigRequest(burn_subtitles=False))

    outside_asset = _write_png(tmp_path / "outside" / "topic.png", (20, 90, 210))
    scene.visual_source = str(outside_asset)
    with pytest.raises(AssetUnavailableError, match="inside the local asset directory"):
        adapter.assemble_media("escape", "escape", [scene], str(audio), 0.8, MediaRenderConfigRequest(burn_subtitles=False))
    assert not list((tmp_path / "video").glob("*.mp4"))


def test_corrupt_scene_asset_fails_without_output(tmp_path):
    adapter = _adapter(tmp_path)
    _require_local_ffmpeg(adapter)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    broken = adapter.asset_root / "images" / "corrupt.png"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_bytes(b"not a PNG")
    scene = SceneMediaInput(
        id="broken-scene", scene_order=1, narration="Corrupt media", timing_estimate=0.8,
        visual_source=str(broken),
    )

    with pytest.raises(AssetUnavailableError, match="no decodable visual stream"):
        adapter.assemble_media("corrupt", "corrupt", [scene], str(audio), 0.8, MediaRenderConfigRequest(burn_subtitles=False))
    assert not list((tmp_path / "video").glob("*.mp4"))


def test_two_unrelated_topics_render_their_own_vertical_visuals(tmp_path):
    adapter = _adapter(tmp_path)
    _require_local_ffmpeg(adapter)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    topic_a = _write_png(adapter.asset_root / "screenshots" / "solar-grid.png", (220, 30, 30))
    topic_b = _write_png(adapter.asset_root / "screenshots" / "ocean-sensor.png", (20, 170, 70))

    output_a = _render(adapter, "topic-solar", "solar", audio, topic_a)
    output_b = _render(adapter, "topic-ocean", "ocean", audio, topic_b)

    assert output_a.status == output_b.status == "MOCK"
    assert output_a.resolution == output_b.resolution == "1080x1920"
    assert output_a.quality_report["ffprobe_verified"] is True
    assert output_a.quality_report["width"] == 1080
    assert output_a.quality_report["height"] == 1920
    assert output_a.quality_report["video_codec"] == "h264"
    assert output_a.quality_report["audio_codec"] == "aac"
    assert output_a.quality_report["mock_audio"] is True
    assert output_a.quality_report["passed"] is False

    frame_a = tmp_path / "solar-frame.png"
    frame_b = tmp_path / "ocean-frame.png"
    for source, frame in ((output_a.video_path, frame_a), (output_b.video_path, frame_b)):
        proc = subprocess.run(
            [adapter.ffmpeg_path, "-hide_banner", "-loglevel", "error", "-y", "-i", source, "-frames:v", "1", str(frame)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
    assert frame_a.read_bytes() != frame_b.read_bytes()


def test_landscape_render_burns_required_captions_and_is_ffprobe_verified(tmp_path):
    adapter = _adapter(tmp_path)
    _require_local_ffmpeg(adapter)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    image = _write_png(adapter.asset_root / "images" / "landscape.png", (45, 70, 180), width=160, height=90)
    subtitle = adapter.asset_root / "captions" / "captions.srt"
    subtitle.parent.mkdir(parents=True, exist_ok=True)
    subtitle.write_text("1\n00:00:00,000 --> 00:00:00,700\nLandscape caption test\n", encoding="utf-8")

    output = _render(adapter, "landscape-script", "landscape-package", audio, image, resolution="horizontal_16_9", subtitles=subtitle)

    assert output.resolution == "1920x1080"
    assert output.quality_report["width"] == 1920
    assert output.quality_report["height"] == 1080
    assert output.quality_report["subtitles_requested"] is True
    assert output.quality_report["subtitles_burned"] is True
    assert output.quality_report["ffprobe_verified"] is True
    assert abs(output.quality_report["video_duration_sec"] - output.quality_report["audio_duration_sec"]) <= 0.25
    assert output.quality_report["passed"] is False  # The fixture narration is explicitly mock audio.


def test_burned_caption_staging_is_resolution_aware_and_bottom_aligned(tmp_path):
    source = tmp_path / "captions.vtt"
    source.write_text(
        "WEBVTT\n\nchapter-one\n00:00:00.000 --> 00:00:01.235 align:start\n"
        "Solar panels store energy.\n\n00:00:01.500 --> 00:00:02.000\nBattery backup follows.\n",
        encoding="utf-8",
    )
    vertical = tmp_path / "vertical.ass"
    landscape = tmp_path / "landscape.ass"

    FFmpegMediaAdapter._write_ass_subtitles(source, vertical, 1080, 1920)
    FFmpegMediaAdapter._write_ass_subtitles(source, landscape, 1920, 1080)

    vertical_text = vertical.read_text(encoding="utf-8")
    landscape_text = landscape.read_text(encoding="utf-8")
    assert "PlayResX: 1080" in vertical_text and "PlayResY: 1920" in vertical_text
    assert "Style: Default,Arial,42," in vertical_text
    assert "Style: Default,Arial,34," in landscape_text
    assert "Alignment, MarginL, MarginR, MarginV, Encoding" in vertical_text
    assert ",3,1,0,2,60,60,120,1" in vertical_text
    assert "Dialogue: 0,0:00:00.00,0:00:01.24,Default,,0,0,0,,Solar panels store energy." in vertical_text
    assert "Dialogue: 0,0:00:01.50,0:00:02.00,Default,,0,0,0,,Battery backup follows." in vertical_text
    assert "00:00:00.000 -->" not in vertical_text


def test_invalid_required_caption_file_fails_before_rendering(tmp_path):
    adapter = _adapter(tmp_path)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    image = _write_png(adapter.asset_root / "images" / "frame.png", (120, 30, 140))
    subtitle = adapter.asset_root / "captions" / "invalid.srt"
    subtitle.parent.mkdir(parents=True, exist_ok=True)
    subtitle.write_text("This file contains no timed caption.", encoding="utf-8")

    with pytest.raises(MediaRenderError, match="no valid timed captions"):
        _render(adapter, "invalid-caption", "invalid-caption", audio, image, subtitles=subtitle)
    assert not list((tmp_path / "video").glob("*.mp4"))


def test_subtitle_filter_failure_does_not_retry_without_captions(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path)
    _require_local_ffmpeg(adapter)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    image = _write_png(adapter.asset_root / "images" / "frame.png", (120, 30, 140))
    subtitle = adapter.asset_root / "captions" / "bad-filter.srt"
    subtitle.parent.mkdir(parents=True, exist_ok=True)
    subtitle.write_text("1\n00:00:00,000 --> 00:00:00,700\nCaption must remain mandatory\n", encoding="utf-8")
    real_run = subprocess.run
    render_commands = []

    def fail_burn_in(command, *args, **kwargs):
        if command and command[0] == adapter.ffmpeg_path and "-filter_complex" in command:
            render_commands.append(command)
            return subprocess.CompletedProcess(command, 1, "", "subtitle filter failed")
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_burn_in)
    with pytest.raises(MediaRenderError, match="no caption-free retry") as error:
        _render(adapter, "caption-failure", "caption-failure", audio, image, subtitles=subtitle)

    assert error.value.stage == "subtitles"
    assert len(render_commands) == 1
    assert "subtitles=filename=" in " ".join(render_commands[0])
    assert not list((tmp_path / "video").glob("*.mp4"))


def test_invalid_ffmpeg_output_is_rejected_by_ffprobe_and_removed(tmp_path, monkeypatch):
    adapter = _adapter(tmp_path)
    _require_local_ffmpeg(adapter)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    image = _write_png(adapter.asset_root / "images" / "frame.png", (120, 130, 40))
    real_run = subprocess.run

    def write_invalid_mp4(command, *args, **kwargs):
        if command and command[0] == adapter.ffmpeg_path and "-filter_complex" in command:
            Path(command[-1]).write_bytes(b"not an mp4 container".ljust(2048, b"!"))
            return subprocess.CompletedProcess(command, 0, "", "")
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", write_invalid_mp4)
    with pytest.raises(MediaRenderError, match="FFprobe rejected rendered MP4"):
        _render(adapter, "invalid-mp4", "invalid-mp4", audio, image)
    assert not list((tmp_path / "video").glob("*.mp4"))


def test_audio_video_scene_duration_mismatch_fails_before_render(tmp_path):
    adapter = _adapter(tmp_path)
    _require_local_ffmpeg(adapter)
    audio = _write_wav(adapter.asset_root / "audio" / "narration.wav")
    image = _write_png(adapter.asset_root / "images" / "frame.png", (10, 120, 230))
    scene = SceneMediaInput(
        id="mismatch", scene_order=1, narration="Mismatch", timing_estimate=0.4,
        visual_source=str(image), actual_audio_duration_sec=0.4,
    )

    with pytest.raises(MediaRenderError, match="differ from the measured master audio") as error:
        adapter.assemble_media(
            "duration-mismatch", "duration-mismatch", [scene], str(audio), 0.4,
            MediaRenderConfigRequest(burn_subtitles=False), audio_is_mock=True,
        )
    assert error.value.stage == "timeline"
    assert not list((tmp_path / "video").glob("*.mp4"))


def test_svg_external_resources_are_rejected(tmp_path):
    adapter = _adapter(tmp_path)
    svg = adapter.asset_root / "images" / "unsafe.svg"
    svg.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/track.png" /></svg>',
        encoding="utf-8",
    )
    with pytest.raises(AssetUnavailableError, match="external resource references"):
        adapter._validate_svg(svg)


def test_svg_is_rasterized_from_topic_asset_when_headless_browser_exists(tmp_path):
    adapter = _adapter(tmp_path)
    if not adapter.svg_renderer_path:
        pytest.skip("Headless Edge/Chrome is not installed.")
    svg = adapter.asset_root / "images" / "topic-scene.svg"
    svg.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90" viewBox="0 0 160 90">'
        '<rect width="160" height="90" fill="#007f5f"/><circle cx="80" cy="45" r="28" fill="#fcbf49"/>'
        '</svg>',
        encoding="utf-8",
    )
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        png = adapter._rasterize_svg(svg, Path(temp), "svg-topic")
        assert png.is_file()
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_subtitle_timing_orders_scenes_and_reports_proportional_limit(tmp_path):
    adapter = SubtitleAdapter(output_dir=str(tmp_path / "subtitles"))
    scenes = [
        SceneMediaInput(id="second", scene_order=2, narration="Second measured scene.", timing_estimate=1.5),
        SceneMediaInput(id="first", scene_order=1, narration="First measured scene.", timing_estimate=1.0),
    ]
    output = adapter.generate_subtitles(
        script_id="timing-script",
        scenes=scenes,
        track_durations={"first": 1.2, "second": 1.6},
        config=SubtitleConfigRequest(format="srt", silence_gap_sec=0.2),
    )
    assert output.script_id == "timing-script"
    assert output.timing_method == "proportional_to_measured_scene_audio"
    assert "proportional estimates" in output.timing_limitation
    first_scene_cues = [cue for cue in output.cues if cue.scene_id == "first"]
    second_scene_cues = [cue for cue in output.cues if cue.scene_id == "second"]
    assert first_scene_cues[0].start_sec == 0.0
    assert second_scene_cues[0].start_sec >= max(cue.end_sec for cue in first_scene_cues) + 0.19


@pytest.mark.asyncio
async def test_media_engine_marks_missing_asset_result_failed(tmp_path):
    engine = MediaEngine()
    engine.ffmpeg_adapter.asset_root = tmp_path / "assets"
    engine.ffmpeg_adapter.asset_root.mkdir(parents=True, exist_ok=True)
    engine.audio_synthesizer.output_dir = engine.ffmpeg_adapter.asset_root / "audio"
    engine.audio_synthesizer.output_dir.mkdir(parents=True, exist_ok=True)
    engine.subtitle_adapter.output_dir = engine.ffmpeg_adapter.asset_root / "subtitles"
    engine.subtitle_adapter.output_dir.mkdir(parents=True, exist_ok=True)
    engine.ffmpeg_adapter.output_dir = tmp_path / "video"
    engine.ffmpeg_adapter.output_dir.mkdir(parents=True, exist_ok=True)

    from app.engines.core.base import EngineContext
    result = await engine.run(EngineContext(
        run_id="missing-assets-run",
        parameters={
            "script_id": "missing-assets",
            "package_id": "missing-assets-package",
            "action": "render",
            "voice_config": {"mock_mode": True},
            "render_config": {"burn_subtitles": False},
            "scenes": [{
                "id": "missing-visual", "scene_order": 1, "narration": "No asset fallback.",
                "timing_estimate": 1.0, "visual_source": None,
            }],
        },
    ))

    assert result.success is False
    assert result.outputs[0]["status"] == "FAILED"
    assert result.outputs[0]["quality_report"]["passed"] is False
    assert "attach a local asset" in result.errors[0]
