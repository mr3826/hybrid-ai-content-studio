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

    # 3. Synthesize voice tracks
    voice_res = await client.post(
        f"/api/v1/media/voice/{script_id}",
        json={"voice_id": "en-US-Studio-Standard", "speed": 1.0},
    )
    assert voice_res.status_code == 200
    media_pkg = voice_res.json()
    assert media_pkg["script_id"] == script_id
    assert media_pkg["status"] == "READY"
    assert media_pkg["total_duration_sec"] > 0
    assert media_pkg["audio_path"] is not None
    assert len(media_pkg["voice_tracks"]) == len(scenes)
    assert len(media_pkg["voice_tracks"][0]["waveform_peaks"]) == 50

    # 4. Generate subtitles
    sub_res = await client.post(
        f"/api/v1/media/subtitles/{script_id}",
        json={"format": "srt", "max_words_per_line": 3},
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["cue_count"] >= 3
    assert "-->" in sub_data["content_text"]

    # 5. Download raw subtitles
    dl_res = await client.get(f"/api/v1/media/subtitles/{script_id}/file?format=srt")
    assert dl_res.status_code == 200
    assert "-->" in dl_res.text

    # 6. Render final media composition
    render_res = await client.post(
        f"/api/v1/media/render/{script_id}",
        json={"resolution": "1080x1920", "fps": 30},
    )
    assert render_res.status_code == 200
    rendered_pkg = render_res.json()
    assert rendered_pkg["status"] == "READY"
    assert rendered_pkg["video_path"] is not None
    assert rendered_pkg["resolution"] == "1080x1920"
    assert rendered_pkg["quality_checks"]["passed"] is True

    # 7. Fetch active media package
    get_pkg_res = await client.get(f"/api/v1/media/script/{script_id}")
    assert get_pkg_res.status_code == 200
    fetched_pkg = get_pkg_res.json()
    assert fetched_pkg["id"] == rendered_pkg["id"]
    assert len(fetched_pkg["voice_tracks"]) == len(scenes)
