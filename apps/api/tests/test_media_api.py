import binascii
import math
from pathlib import Path
import shutil
import struct
import zlib
import uuid

import pytest
from httpx import AsyncClient

from app.api.v1 import media as media_api


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)


def _write_png(path: Path, color: tuple[int, int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 120, 80
    raw = (b"\x00" + bytes(color) * width) * height
    ihdr = struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    return path


def _use_temp_media_dirs(monkeypatch, tmp_path: Path):
    assets = tmp_path / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(media_api.engine.audio_synthesizer, "output_dir", assets / "audio")
    monkeypatch.setattr(media_api.engine.subtitle_adapter, "output_dir", assets / "subtitles")
    monkeypatch.setattr(media_api.engine.ffmpeg_adapter, "output_dir", tmp_path / "video")
    monkeypatch.setattr(media_api.engine.ffmpeg_adapter, "asset_root", assets)
    media_api.engine.audio_synthesizer.output_dir.mkdir(parents=True, exist_ok=True)
    media_api.engine.subtitle_adapter.output_dir.mkdir(parents=True, exist_ok=True)
    media_api.engine.ffmpeg_adapter.output_dir.mkdir(parents=True, exist_ok=True)
    return assets


async def _create_script_and_scenes(client: AsyncClient, name: str):
    family_res = await client.post(
        "/api/v1/content-families",
        json={"title": f"Media API Family ({name})", "content_pillar": "Local Media", "original_value_type": "benchmark", "summary": "Media integration fixture."},
    )
    assert family_res.status_code == 201, family_res.text
    family_id = family_res.json()["id"]
    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical", "platform_target": "youtube", "working_title": f"Media Topic ({name})",
            "angle": "Use topic-specific scene visuals.", "hook_type": "bold_claim",
            "original_value_connection": "Local visual fixture.", "viewer_value": "Verified media pipeline.",
        },
    )
    assert item_res.status_code == 201, item_res.text
    item_id = item_res.json()["id"]
    script_res = await client.post("/api/v1/scripts/generate", json={"content_item_id": item_id, "target_duration_sec": 18})
    assert script_res.status_code == 200, script_res.text
    script_id = script_res.json()["id"]
    scene_res = await client.post(f"/api/v1/scenes/decompose/{script_id}")
    assert scene_res.status_code == 200, scene_res.text
    return item_id, script_id, scene_res.json()


@pytest.mark.asyncio
async def test_media_api_full_flow_uses_installed_voice_catalog_and_mock_is_not_ready(client: AsyncClient, monkeypatch, tmp_path):
    _use_temp_media_dirs(monkeypatch, tmp_path)
    name = uuid.uuid4().hex[:8]
    _, script_id, scenes = await _create_script_and_scenes(client, name)

    voice_catalog = (await client.get("/api/v1/media/voices")).json()
    assert set(voice_catalog) >= {"available", "default_voice_id", "voices", "supported_languages", "unavailable_languages", "message"}
    assert all({"id", "name", "locale", "gender"} <= voice.keys() for voice in voice_catalog["voices"])
    assert not any(voice["id"].endswith("Studio-Standard") for voice in voice_catalog["voices"])
    if voice_catalog["available"]:
        assert voice_catalog["default_voice_id"] in {voice["id"] for voice in voice_catalog["voices"]}
        assert voice_catalog["supported_languages"]

    voice_res = await client.post(
        f"/api/v1/media/voice/{script_id}",
        json={"voice_id": "test-harmonic", "speed": 1.0, "mock_mode": True},
    )
    assert voice_res.status_code == 200, voice_res.text
    package = voice_res.json()
    assert package["status"] == "MOCK"
    assert package["quality_checks"]["passed"] is False
    assert len(package["voice_tracks"]) == len(scenes)
    assert all(track["is_mock"] is True for track in package["voice_tracks"])
    assert all(track["synthesis_mode"] == "mock_harmonic" for track in package["voice_tracks"])

    subtitles_res = await client.post(
        f"/api/v1/media/subtitles/{script_id}",
        json={"format": "srt", "max_words_per_line": 3, "silence_gap_sec": 0.2},
    )
    assert subtitles_res.status_code == 200, subtitles_res.text
    subtitles = subtitles_res.json()
    assert subtitles["script_id"] == script_id
    assert subtitles["cue_count"] >= 1
    assert "-->" in subtitles["content_text"]
    assert subtitles["timing_method"] == "proportional_to_measured_scene_audio"
    assert "proportional estimates" in subtitles["timing_limitation"]

    # Decomposed scenes do not have production visuals. Rendering must fail rather than borrow demo cards.
    render_res = await client.post(
        f"/api/v1/media/render/{script_id}",
        json={"resolution": "horizontal_16_9", "fps": 30, "burn_subtitles": True},
    )
    assert render_res.status_code == 422, render_res.text
    media_res = await client.get(f"/api/v1/media/script/{script_id}")
    failed = media_res.json()
    assert failed["status"] == "FAILED"
    assert failed["video_path"] is None
    assert failed["quality_checks"]["passed"] is False
    assert "asset" in failed["quality_checks"]["issues"][0].lower()


@pytest.mark.asyncio
async def test_media_api_real_ffmpeg_artifact_is_mock_labeled_and_dimension_checked(client: AsyncClient, monkeypatch, tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("This integration requires local FFmpeg and FFprobe.")
    assets = _use_temp_media_dirs(monkeypatch, tmp_path)
    name = uuid.uuid4().hex[:8]
    _, script_id, scenes = await _create_script_and_scenes(client, name)

    for index, scene in enumerate(scenes):
        color = ((220, 40, 35), (30, 165, 75), (35, 70, 210))[index % 3]
        image = _write_png(assets / "topic" / f"{name}-scene-{index}.png", color)
        response = await client.put(
            f"/api/v1/scenes/{scene['id']}",
            json={"visual_source": str(image), "status": "READY", "timing_estimate": 0.6},
        )
        assert response.status_code == 200, response.text

    voice_res = await client.post(
        f"/api/v1/media/voice/{script_id}",
        json={"mock_mode": True},
    )
    assert voice_res.status_code == 200, voice_res.text
    render_res = await client.post(
        f"/api/v1/media/render/{script_id}",
        json={"resolution": "horizontal_16_9", "fps": 30, "burn_subtitles": True},
    )
    assert render_res.status_code == 200, render_res.text
    package = render_res.json()
    assert package["status"] == "MOCK"
    assert package["video_path"] and Path(package["video_path"]).is_file()
    assert package["resolution"] == "1920x1080"
    assert package["quality_checks"]["ffprobe_verified"] is True
    assert package["quality_checks"]["width"] == 1920
    assert package["quality_checks"]["height"] == 1080
    assert package["quality_checks"]["subtitles_burned"] is True
    assert package["quality_checks"]["passed"] is False
    assert package["quality_checks"]["mock_audio"] is True
    assert package["quality_checks"]["duration_sync_delta"] <= 0.25


@pytest.mark.asyncio
async def test_media_job_endpoint_queues_local_worker_job(client: AsyncClient, monkeypatch, tmp_path):
    _use_temp_media_dirs(monkeypatch, tmp_path)
    name = uuid.uuid4().hex[:8]
    _, script_id, scenes = await _create_script_and_scenes(client, name)
    response = await client.post(
        f"/api/v1/media/jobs/{script_id}",
        json={
            "action": "synthesize",
            "voice_config": {"mock_mode": False},
            "render_config": {"resolution": "vertical_9_16", "burn_subtitles": True},
        },
    )
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["engine_id"] == "media"
    assert job["status"] == "pending"
    params = job["payload"]["parameters"]
    assert params["script_id"] == script_id
    assert params["action"] == "synthesize"
    assert len(params["scenes"]) == len(scenes)
    cancel_res = await client.post(f"/api/v1/jobs/{job['id']}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"
