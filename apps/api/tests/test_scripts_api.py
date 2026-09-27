import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scripts_health(client: AsyncClient):
    res = await client.get("/api/v1/scripts/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["engine_id"] == "content"


@pytest.mark.asyncio
async def test_script_generation_and_refinement_flow(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Create parent Content Family
    family_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"RTX 5090 Local Inference Family ({test_id})",
            "content_pillar": "Hardware Benchmarks",
            "original_value_type": "benchmark",
            "summary": "Real laboratory tests measuring tokens per second across local quantized models.",
        },
    )
    assert family_res.status_code == 201
    family = family_res.json()
    family_id = family["id"]

    # 2. Add child content item
    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"RTX 5090 Speed Test: 120 Tokens/Sec ({test_id})",
            "angle": "Empirical latency measurements prove local setup beats paid cloud APIs.",
            "hook_type": "bold_claim",
            "original_value_connection": "Verified hardware telemetry from our local testing rig.",
            "viewer_value": "Learn how to configure batch sizes for maximum throughput.",
        },
    )
    assert item_res.status_code == 201
    item = item_res.json()
    item_id = item["id"]

    # 3. Generate evidence-grounded script draft
    gen_res = await client.post(
        "/api/v1/scripts/generate",
        json={
            "content_item_id": item_id,
            "target_duration_sec": 60,
        },
    )
    assert gen_res.status_code == 200
    script = gen_res.json()
    script_id = script["id"]
    assert script["format"] == "short_vertical"
    assert len(script["sections"]) == 5
    assert script["status"] in ("DRAFT", "SCRIPT_REVIEW")
    assert script["total_word_count"] > 0
    assert script["estimated_duration_sec"] > 0

    # Verify item status transitioned to SCRIPT_REVIEW
    check_item = await client.get(f"/api/v1/content-items/{item_id}")
    assert check_item.status_code == 200
    assert check_item.json()["status"] == "SCRIPT_REVIEW"

    # 4. Fetch script by item id
    by_item_res = await client.get(f"/api/v1/scripts/item/{item_id}")
    assert by_item_res.status_code == 200
    assert by_item_res.json()["id"] == script_id

    # 5. Section refinement (Shorten)
    hook_sec = script["sections"][0]
    sec_id = hook_sec["id"]
    refine_res = await client.post(
        f"/api/v1/scripts/{script_id}/sections/{sec_id}/refine",
        json={
            "refinement_type": "shorten",
            "guidance": "Make opening punchy for 45s target",
        },
    )
    assert refine_res.status_code == 200
    refine_data = refine_res.json()
    assert "refinement" in refine_data
    assert refine_data["refinement"]["section_id"] == sec_id

    # 6. Manual edit of section
    edit_res = await client.patch(
        f"/api/v1/scripts/{script_id}/sections/{sec_id}",
        json={
            "narration": "Stop paying cloud AI providers. Our local tests clocked 120 tokens per second on consumer hardware.",
            "visual_cue": "Close up of glowing RTX card with hardware temperature overlay.",
        },
    )
    assert edit_res.status_code == 200
    updated_script = edit_res.json()
    updated_hook = next(s for s in updated_script["sections"] if s["id"] == sec_id)
    assert "120 tokens per second" in updated_hook["narration"]

    # 7. Check revisions list
    revs_res = await client.get(f"/api/v1/scripts/{script_id}/revisions")
    assert revs_res.status_code == 200
    revisions = revs_res.json()
    assert len(revisions) >= 3 # initial_generation, shorten, manual_edit

    # 8. Restore previous revision
    first_rev = revisions[-1] # oldest revision
    restore_res = await client.post(
        f"/api/v1/scripts/{script_id}/revisions/{first_rev['id']}/restore"
    )
    assert restore_res.status_code == 200

    # 9. Quality Check
    qc_res = await client.post(f"/api/v1/scripts/{script_id}/quality-check")
    assert qc_res.status_code == 200
    qc_data = qc_res.json()
    assert "dimension_scores" in qc_data
    assert "evidence" in qc_data["dimension_scores"]
    assert "brand" in qc_data["dimension_scores"]
    assert "originality" in qc_data["dimension_scores"]

    restored_script = restore_res.json()
    active_hook_id = restored_script["sections"][0]["id"]

    # 10. Human Gate Approval
    # First test rejection if we inject a banned cliché
    banned_edit = await client.patch(
        f"/api/v1/scripts/{script_id}/sections/{active_hook_id}",
        json={
            "narration": "This game-changer model is completely revolutionary and will unleash your AI power.",
        },
    )
    assert banned_edit.status_code == 200

    # Attempt to approve without override -> must fail with 422
    fail_approve = await client.post(
        f"/api/v1/scripts/{script_id}/approve",
        json={"reviewer": "test_creator"},
    )
    assert fail_approve.status_code == 422
    assert "blocking_reasons" in fail_approve.json()["detail"]

    # Approve with explicit human override
    override_approve = await client.post(
        f"/api/v1/scripts/{script_id}/approve",
        json={
            "reviewer": "chief_editor",
            "override_reason": "Satirical emphasis on cliché in tech marketing.",
        },
    )
    assert override_approve.status_code == 200
    approved_script = override_approve.json()
    assert approved_script["status"] == "SCRIPT_APPROVED"
    assert approved_script["is_approved"] is True
    assert approved_script["approved_by"] == "chief_editor"

    # Verify ContentItem transitioned to SCRIPT_APPROVED
    item_approved = await client.get(f"/api/v1/content-items/{item_id}")
    assert item_approved.status_code == 200
    assert item_approved.json()["status"] == "SCRIPT_APPROVED"
    assert item_approved.json()["script_version_id"] == script_id
