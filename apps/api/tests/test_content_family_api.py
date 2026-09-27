import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_content_family_health(client: AsyncClient):
    res = await client.get("/api/v1/content-families/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_content_family_lifecycle_and_economics(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]
    title = f"Local LLM Benchmark Family ({test_id})"

    # 1. Create a Content Family with shared research & experiment investment
    create_payload = {
        "title": title,
        "content_pillar": "Hardware Benchmarks",
        "original_value_type": "benchmark",
        "summary": "Comparing tokens/sec and VRAM saturation across Ollama and llama.cpp on M4 Max.",
        "research_cost": 1.50,
        "experiment_cost": 0.00,  # Local hardware
        "ai_cost": 0.35,
        "media_cost": 0.00,
        "manual_time_minutes": 45,
        "local_compute_seconds": 320.0,
    }
    res = await client.post("/api/v1/content-families", json=create_payload)
    assert res.status_code == 201
    family = res.json()
    family_id = family["id"]
    assert family["title"] == title
    assert family["status"] == "DRAFT"

    # 2. List families
    res = await client.get("/api/v1/content-families")
    assert res.status_code == 200
    families = res.json()
    assert any(f["id"] == family_id for f in families)

    # 3. Request AI/algorithmic child suggestions
    res = await client.post(f"/api/v1/content-families/{family_id}/suggest-items")
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions["proposals"]) >= 4

    # 4. Add child items
    item1_payload = {
        "format": "youtube_long",
        "platform_target": "youtube",
        "working_title": f"M4 Max Benchmark: Ollama vs llama.cpp ({test_id})",
        "angle": "Comprehensive 15-minute breakdown testing prompt processing throughput and KV cache limits.",
        "hook_type": "curiosity_gap",
        "status": "PLANNED",
        "incremental_cost": 0.50,
        "manual_time_minutes": 60,
        "local_compute_seconds": 180.0,
        "original_value_connection": "Delivers the complete side-by-side benchmark table with reproducible setup.",
        "viewer_value": "Shows viewer exact hardware throughput before buying.",
    }
    res = await client.post(f"/api/v1/content-families/{family_id}/items", json=item1_payload)
    assert res.status_code == 201
    item1 = res.json()
    item1_id = item1["id"]
    assert item1["format"] == "youtube_long"

    item2_payload = {
        "format": "short_vertical",
        "platform_target": "youtube",
        "working_title": f"The Faster Mac LLM ({test_id})",
        "angle": "Quick 45-second test comparing generation speed on 14B model.",
        "hook_type": "bold_claim",
        "status": "PLANNED",
        "incremental_cost": 0.10,
        "manual_time_minutes": 20,
        "local_compute_seconds": 60.0,
        "original_value_connection": "Visualizes the speed difference in a quick chart.",
        "viewer_value": "Provides the 10-second answer to which tool runs faster.",
    }
    res = await client.post(f"/api/v1/content-families/{family_id}/items", json=item2_payload)
    assert res.status_code == 201
    item2 = res.json()

    # 5. Fetch Family detail and check economics aggregation
    res = await client.get(f"/api/v1/content-families/{family_id}")
    assert res.status_code == 200
    detail = res.json()
    assert len(detail["items"]) == 2

    econ = detail["economics"]
    # Shared cost = 1.50 + 0.35 = 1.85
    assert econ["shared_family_cost"] == 1.85
    # Incremental = 0.50 + 0.10 = 0.60
    assert econ["total_incremental_cost"] == 0.60
    # Total = 2.45
    assert econ["total_family_cost"] == 2.45
    # Cost per child = 2.45 / 2 = 1.225
    assert econ["cost_per_child"] == 1.225
    assert econ["total_time_minutes"] == 45 + 60 + 20

    # 6. Approve Family Plan
    res = await client.post(
        f"/api/v1/content-families/{family_id}/approve",
        json={"reviewer": "lead_producer"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "READY_FOR_CONTENT"

    # 7. Archive Family
    res = await client.post(f"/api/v1/content-families/{family_id}/archive")
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_evidence_selection_without_claim_duplication(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Create an empirical claim in Evidence Engine
    claim_res = await client.post(
        "/api/v1/evidence/claims",
        json={
            "text": f"M4 Max achieves 48.2 tokens/sec under 16k context ({test_id})",
            "claim_type": "original_measurement",
            "confidence": 0.99,
        },
    )
    assert claim_res.status_code == 201
    claim = claim_res.json()
    claim_id = claim["id"]

    # 2. Create Content Family
    fam_res = await client.post(
        "/api/v1/content-families",
        json={"title": f"Speed Test Family ({test_id})"},
    )
    assert fam_res.status_code == 201
    family_id = fam_res.json()["id"]

    # 3. Create Child Content Item
    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "tiktok",
            "working_title": f"M4 Max Speed Winner ({test_id})",
            "angle": "Spotlighting 48 tokens/sec throughput metric with terminal overlay.",
            "hook_type": "bold_claim",
            "original_value_connection": "Highlights verified speed measurement.",
            "viewer_value": "Shows real-world performance.",
        },
    )
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    # 4. Link claim to child
    link_res = await client.post(
        f"/api/v1/content-items/{item_id}/evidence",
        json={
            "claim_id": claim_id,
            "relevance_note": "Featured in opening 5 seconds on-screen hook.",
            "is_primary": True,
        },
    )
    assert link_res.status_code == 201
    link_data = link_res.json()
    assert link_data["claim_id"] == claim_id
    assert link_data["is_primary"] is True

    # 5. Fetch child and verify evidence selection
    get_res = await client.get(f"/api/v1/content-items/{item_id}")
    assert get_res.status_code == 200
    item_data = get_res.json()
    assert len(item_data["evidence_selections"]) == 1
    assert item_data["evidence_selections"][0]["claim_id"] == claim_id
    assert "48.2 tokens/sec" in item_data["evidence_selections"][0]["claim_text"]

    # 6. Unlink claim
    unlink_res = await client.delete(f"/api/v1/content-items/{item_id}/evidence/{claim_id}")
    assert unlink_res.status_code == 200
    assert unlink_res.json()["unlinked"] is True


@pytest.mark.asyncio
async def test_child_item_validation_and_phase11_invariants(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # Create Family
    fam_res = await client.post(
        "/api/v1/content-families",
        json={"title": f"Validation Test Family ({test_id})"},
    )
    family_id = fam_res.json()["id"]

    # 1. Reject invalid format
    inv_format_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "hologram_vlog",
            "working_title": "Invalid format test",
            "angle": "Valid description length that is long enough.",
            "original_value_connection": "Connection",
        },
    )
    assert inv_format_res.status_code == 400
    assert "not one of supported formats" in inv_format_res.json()["detail"]

    # 2. Reject too-short angle (prevents generic recap)
    inv_angle_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "social_post",
            "working_title": "Too short angle",
            "angle": "Brief",
            "original_value_connection": "Connection",
        },
    )
    assert inv_angle_res.status_code == 400
    assert "must be at least 15 characters" in inv_angle_res.json()["detail"]

    # 3. Create valid child
    valid_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "newsletter",
            "working_title": "Technical Setup Guide",
            "angle": "Step-by-step reproduction guide with copy-paste terminal configs.",
            "original_value_connection": "Provides the complete reproduction setup.",
            "viewer_value": "Immediate implementation guide.",
        },
    )
    assert valid_res.status_code == 201
    item_id = valid_res.json()["id"]

    # 4. Invariant: child CANNOT become SCRIPT_APPROVED in Phase 11
    script_approve_res = await client.patch(
        f"/api/v1/content-items/{item_id}",
        json={"status": "SCRIPT_APPROVED"},
    )
    assert script_approve_res.status_code == 400
    assert "cannot become SCRIPT_APPROVED" in script_approve_res.json()["detail"]

    # 5. Delete child item
    del_res = await client.delete(f"/api/v1/content-items/{item_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
