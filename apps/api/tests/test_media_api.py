import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_media_api_full_flow(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Setup a test script with decomposed scenes
    family_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Media API Test Family ({test_id})",
            "content_pillar": "Media Production",
            "original_value_type": "benchmark",
            "summary": "Real laboratory voice and subtitle tests.",
        },
    )
    assert family_res.status_code == 201
    family_id = family_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Media Flow ({test_id})",
            "angle": "Empirical audio synthesis and timed captioning.",
            "hook_type": "bold_claim",
            "original_value_connection": "Verified telemetry.",
            "viewer_value": "Optimal configuration.",
        },
    )
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    gen_res = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 45},
    )
    assert gen_res.status_code == 200
    script_id = gen_res.json()["id"]

    dec_res = await client.post(f"/api/v1/scenes/decompose/{script_id}")
    assert dec_res.status_code == 200
    scenes = dec_res.json()
    assert len(scenes) >= 3

    # 2. List voices
    voices_res = await client.get("/api/v1/media/voices")
    assert voices_res.status_code == 200
    voices = voices_res.json()
    assert len(voices) >= 2
    assert any(v["id"] == "en-US-Studio-Standard" for v in voices)

    # 3. Synthesize voice tracks with profile
    voice_res = await client.post(
        f"/api/v1/media/voice/{script_id}",
        json={"voice_id": "en-US-Studio-Authoritative", "speed": 1.0},
    )
    assert voice_res.status_code == 200
    media_pkg = voice_res.json()
    assert media_pkg["script_id"] == script_id
    assert media_pkg["status"] == "READY"
    assert media_pkg["total_duration_sec"] > 0
    assert media_pkg["audio_path"] is not None
    assert len(media_pkg["voice_tracks"]) == len(scenes)
    assert len(media_pkg["voice_tracks"][0]["waveform_peaks"]) == 50

    # 4. Generate subtitles with pacing metrics
    sub_res = await client.post(
        f"/api/v1/media/subtitles/{script_id}",
        json={"format": "srt", "max_words_per_line": 3, "silence_gap_sec": 0.2},
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["cue_count"] >= 3
    assert "-->" in sub_data["content_text"]
    assert sub_data["avg_cps"] > 0
    assert sub_data["pacing_status"] in ("OPTIMAL", "FAST", "SLOW")

    # 5. Download raw subtitles
    dl_res = await client.get(f"/api/v1/media/subtitles/{script_id}/file?format=srt")
    assert dl_res.status_code == 200
    assert "-->" in dl_res.text

    # 6. Render final media composition with burn_subtitles and resolution normalization
    render_res = await client.post(
        f"/api/v1/media/render/{script_id}",
        json={"resolution": "horizontal_16_9", "fps": 30, "burn_subtitles": True},
    )
    assert render_res.status_code == 200
    rendered_pkg = render_res.json()
    assert rendered_pkg["status"] == "READY"
    assert rendered_pkg["video_path"] is not None
    assert rendered_pkg["resolution"] == "1920x1080"
    assert rendered_pkg["quality_checks"]["passed"] is True
    assert rendered_pkg["quality_report"]["resolution"] == "1920x1080"
    assert "duration_sync_delta" in rendered_pkg["quality_checks"]

    # 7. Fetch active media package
    get_pkg_res = await client.get(f"/api/v1/media/script/{script_id}")
    assert get_pkg_res.status_code == 200
    fetched_pkg = get_pkg_res.json()
    assert fetched_pkg["id"] == rendered_pkg["id"]
    assert len(fetched_pkg["voice_tracks"]) == len(scenes)


@pytest.mark.asyncio
async def test_media_api_auto_generate_and_render(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # Setup script
    family_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Auto Render Test Family ({test_id})",
            "content_pillar": "Tech Demos",
            "original_value_type": "experiment",
            "summary": "Autonomous pipeline render test.",
        },
    )
    family_id = family_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "tiktok",
            "working_title": f"Auto Flow ({test_id})",
            "angle": "One-click compilation test.",
            "hook_type": "question",
            "original_value_connection": "Verified telemetry.",
            "viewer_value": "Streamlined flow.",
        },
    )
    item_id = item_res.json()["id"]

    gen_res = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 30},
    )
    script_id = gen_res.json()["id"]

    await client.post(f"/api/v1/scenes/decompose/{script_id}")

    # Directly call render with burn_subtitles=True without prior voice or subtitle generation
    render_res = await client.post(
        f"/api/v1/media/render/{script_id}",
        json={"resolution": "vertical_9_16", "fps": 30, "burn_subtitles": True},
    )
    assert render_res.status_code == 200
    res_data = render_res.json()
    assert res_data["status"] == "READY"
    assert res_data["audio_path"] is not None
    assert res_data["subtitle_path"] is not None
    assert res_data["video_path"] is not None
    assert res_data["resolution"] == "1080x1920"
    assert res_data["quality_checks"]["passed"] is True
