import io
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scene_studio_api_full_flow(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Setup a test script with sections
    family_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Scene Studio Test Family ({test_id})",
            "content_pillar": "Local Studio",
            "original_value_type": "benchmark",
            "summary": "Real laboratory tests measuring tokens per second.",
        },
    )
    assert family_res.status_code == 201
    family_id = family_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Local AI Speed ({test_id})",
            "angle": "Empirical latency measurements.",
            "hook_type": "bold_claim",
            "original_value_connection": "Verified hardware telemetry.",
            "viewer_value": "Optimal configuration.",
        },
    )
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    gen_res = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 60},
    )
    assert gen_res.status_code == 200
    script_id = gen_res.json()["id"]

    # 2. Decompose script into scenes
    dec_res = await client.post(f"/api/v1/scenes/decompose/{script_id}")
    assert dec_res.status_code == 200
    scenes = dec_res.json()
    assert len(scenes) >= 3
    assert scenes[0]["scene_order"] == 1
    first_scene_id = scenes[0]["id"]

    # 3. List script scenes
    list_res = await client.get(f"/api/v1/scenes/script/{script_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == len(scenes)

    # 4. Get and update scene
    get_res = await client.get(f"/api/v1/scenes/{first_scene_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == first_scene_id

    update_res = await client.put(
        f"/api/v1/scenes/{first_scene_id}",
        json={
            "timing_estimate": 4.5,
            "on_screen_text": "UPDATED HOOK METRIC",
            "visual_type": "code_terminal",
        },
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["timing_estimate"] == 4.5
    assert updated["on_screen_text"] == "UPDATED HOOK METRIC"
    assert updated["visual_type"] == "code_terminal"

    # 5. Generate local deterministic placeholder visual card
    gen_placeholder_res = await client.post(f"/api/v1/scenes/generate-placeholder/{first_scene_id}")
    assert gen_placeholder_res.status_code == 200
    with_placeholder = gen_placeholder_res.json()
    assert with_placeholder["visual_source"] is not None
    assert with_placeholder["visual_source"].endswith(".svg")
    assert with_placeholder["status"] == "MOCK"

    # 6. Validate storyboard
    val_res = await client.post(f"/api/v1/scenes/validate-storyboard/{script_id}")
    assert val_res.status_code == 200
    validation = val_res.json()
    assert "total_scenes" in validation
    assert "total_duration_sec" in validation
    assert "empirical_visual_ratio" in validation
    assert validation["total_scenes"] >= 3

    # 7. Reorder scenes
    scene_ids = [s["id"] for s in scenes]
    reversed_ids = list(reversed(scene_ids))
    reorder_res = await client.post(
        f"/api/v1/scenes/reorder/{script_id}",
        json={"scene_ids": reversed_ids},
    )
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()
    assert reordered[0]["id"] == reversed_ids[0]
    assert reordered[0]["scene_order"] == 1

    # 8. Create manual scene
    manual_scene_res = await client.post(
        "/api/v1/scenes",
        json={
            "script_id": script_id,
            "scene_order": len(scenes) + 1,
            "narration": "Manual scene bonus benchmark.",
            "timing_estimate": 3.0,
            "visual_type": "benchmark_chart",
        },
    )
    assert manual_scene_res.status_code == 201
    manual_scene_id = manual_scene_res.json()["id"]

    # 9. Delete manual scene
    del_res = await client.delete(f"/api/v1/scenes/{manual_scene_id}")
    assert del_res.status_code == 204

    # 10. Test Media Asset Registration and Listing
    dummy_svg_b64 = "PHN2Zz48Y2lyY2xlIHI9JzEwJy8+PC9zdmc+"  # base64 for <svg><circle r='10'/></svg>
    asset_payload = {
        "name": "Benchmark Test Circle Icon",
        "file_name": "test_circle.svg",
        "file_content_base64": dummy_svg_b64,
        "asset_type": "chart",
        "tags": ["benchmark", "telemetry", "chart"],
        "license_type": "Self-Created",
    }
    upload_res = await client.post("/api/v1/scenes/assets", json=asset_payload)
    assert upload_res.status_code == 201
    uploaded_asset = upload_res.json()
    assert uploaded_asset["name"] == "Benchmark Test Circle Icon"
    assert uploaded_asset["visual_priority"] == 2  # chart is rank 2

    # List media assets
    assets_res = await client.get("/api/v1/scenes/assets?query=Benchmark")
    assert assets_res.status_code == 200
    assert len(assets_res.json()) >= 1
