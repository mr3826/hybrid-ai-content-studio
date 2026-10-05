import uuid
from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_quality_gate_api_full_flow(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Create content family
    fam_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Quality Gate Flow ({test_id})",
            "content_pillar": "Core Systems",
            "original_value_type": "benchmark",
            "summary": "Full quality gate evaluation testing.",
        },
    )
    assert fam_res.status_code == 201
    family_id = fam_res.json()["id"]

    # 2. Create child content item
    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Quality Gate Target ({test_id})",
            "angle": "Empirical testing with zero cloud API dependencies.",
            "hook_type": "bold_claim",
            "original_value_connection": "Local benchmark scripts and verified measurements.",
            "viewer_value": "Step by step command tutorial.",
        },
    )
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    # 3. Generate script draft
    gen_res = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id},
    )
    assert gen_res.status_code == 200
    script_id = gen_res.json()["id"]

    # 4. Fetch Quality Gate Audit
    qg_res = await client.get(f"/api/v1/quality-gate/item/{item_id}")
    assert qg_res.status_code == 200
    qg_data = qg_res.json()

    assert qg_data["content_item_id"] == item_id
    assert qg_data["script_id"] == script_id
    assert len(qg_data["dimensions"]) == 9
    assert "overall_score" in qg_data
    assert "status" in qg_data

    # Verify all 9 dimension names
    dim_ids = [d["id"] for d in qg_data["dimensions"]]
    for expected_dim in [
        "evidence_quality",
        "brand_fit",
        "originality",
        "viewer_value",
        "niche_fit",
        "repetition_intelligence",
        "asset_rights",
        "media_qc",
        "estimated_cost",
    ]:
        assert expected_dim in dim_ids

    # 5. Force re-evaluation
    eval_res = await client.post(f"/api/v1/quality-gate/evaluate/{item_id}")
    assert eval_res.status_code == 200
    assert eval_res.json()["content_item_id"] == item_id

    # 6. Final Quality Gate Approval
    app_res = await client.post(
        f"/api/v1/quality-gate/approve/{item_id}",
        json={
            "approved_by": "Test Creator",
            "notes": "All 9 quality dimensions verified and approved.",
        },
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["is_approved"] is True
    assert app_data["status"] == "FINAL_APPROVED"
    assert app_data["unlocked_export"] is True

    # 7. Check Summary Endpoint
    summary_res = await client.get("/api/v1/quality-gate/summary")
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["total_items"] >= 1
    assert summary_data["final_approved_count"] >= 1
