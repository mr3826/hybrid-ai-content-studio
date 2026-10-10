import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.script import ScriptDraft
from app.repositories.quality_gate_repository import QualityGateRepository


@pytest.mark.asyncio
async def test_export_health(client: AsyncClient):
    res = await client.get("/api/v1/export/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "supported_platforms" in data["details"]
    assert "youtube" in data["details"]["supported_platforms"]


@pytest.mark.asyncio
async def test_export_gate_blocks_unapproved_script(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Create family
    fam_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Gate Test Family ({test_id})",
            "content_pillar": "Coding Agents",
            "original_value_type": "benchmark",
            "summary": "Benchmarking unapproved export blocks.",
        },
    )
    assert fam_res.status_code == 201
    family_id = fam_res.json()["id"]

    # 2. Create item
    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Unapproved Item ({test_id})",
            "angle": "Testing gate failure without approval.",
            "hook_type": "bold_claim",
            "original_value_connection": "Lab test.",
            "viewer_value": "Gate integrity test.",
        },
    )
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    # 3. Attempt export before script even exists -> should return 422
    exp_res1 = await client.post(f"/api/v1/export/{item_id}")
    assert exp_res1.status_code == 422
    assert "No script draft exists" in exp_res1.json()["detail"]

    # 4. Generate draft (status = SCRIPT_REVIEW, is_approved = False)
    gen_res = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id},
    )
    assert gen_res.status_code == 200

    # 5. Attempt export while unapproved -> must return 422 Human Quality Gate Block!
    exp_res2 = await client.post(f"/api/v1/export/{item_id}")
    assert exp_res2.status_code == 422
    assert "Human Quality Gate Block" in exp_res2.json()["detail"]


@pytest.mark.asyncio
async def test_full_export_and_publishing_flow(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Create family
    fam_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Publishing Flow Family ({test_id})",
            "content_pillar": "Workflow Builds",
            "original_value_type": "tutorial",
            "summary": "Laboratory workflow testing.",
        },
    )
    assert fam_res.status_code == 201
    family_id = fam_res.json()["id"]

    # 2. Create child item
    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Automated Local Build ({test_id})",
            "angle": "Empirical evidence showing local workflows save time.",
            "hook_type": "curiosity_gap",
            "original_value_connection": "Reproducible benchmark scripts.",
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

    # 4. Approve script via Human Quality Gate
    app_res = await client.post(
        f"/api/v1/scripts/{script_id}/approve",
        json={"notes": "Approved for testing Phase 13 export."},
    )
    assert app_res.status_code == 200
    assert app_res.json()["is_approved"] is True

    # Verify item status is now SCRIPT_APPROVED
    check_item = await client.get(f"/api/v1/content-items/{item_id}")
    assert check_item.status_code == 200
    assert check_item.json()["status"] == "SCRIPT_APPROVED"

    # 4b. Approve Final Creator Quality Gate (mandatory invariant before export)
    qg_eval_res = await client.post(f"/api/v1/quality-gate/evaluate/{item_id}")
    assert qg_eval_res.status_code == 200

    qg_app_res = await client.post(
        f"/api/v1/quality-gate/approve/{item_id}",
        json={"approved_by": "Test Creator", "notes": "Approved for export."},
    )
    assert qg_app_res.status_code == 200
    assert qg_app_res.json()["is_approved"] is True

    # 5. Trigger Export Package generation
    exp_res = await client.post(f"/api/v1/export/{item_id}")
    assert exp_res.status_code == 200
    pkg = exp_res.json()
    assert pkg["content_item_id"] == item_id
    assert pkg["package_slug"].endswith(f"automated-local-build--{test_id}")
    assert "sources.md" in pkg["files"]
    assert "manifest.json" in pkg["files"]
    assert "youtube/title.txt" in pkg["files"]
    assert len(pkg["checksum"]) == 64

    # Verify ContentItem transitioned to EXPORTED
    check_exported = await client.get(f"/api/v1/content-items/{item_id}")
    assert check_exported.json()["status"] == "EXPORTED"

    # 6. Fetch Export Package by Item ID
    by_item_res = await client.get(f"/api/v1/export/item/{item_id}")
    assert by_item_res.status_code == 200
    assert by_item_res.json()["id"] == pkg["id"]

    # 7. Download ZIP Archive
    zip_res = await client.get(f"/api/v1/export/item/{item_id}/download")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert len(zip_res.content) > 100

    # 8. Fetch Publishing Overview
    overview_res = await client.get(f"/api/v1/publishing/item/{item_id}")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["content_item"]["id"] == item_id
    assert overview["export_package"]["id"] == pkg["id"]
    assert len(overview["publications"]) == 4

    platforms_present = {p["platform"]: p for p in overview["publications"]}
    assert "youtube" in platforms_present
    assert "facebook" in platforms_present
    assert "instagram" in platforms_present
    assert "tiktok" in platforms_present
    assert platforms_present["youtube"]["status"] == "NOT_READY"

    # 9. Update YouTube checklist items
    yt_pub = platforms_present["youtube"]
    yt_pub_id = yt_pub["id"]

    patch_checklist_res = await client.patch(
        f"/api/v1/publishing/{yt_pub_id}",
        json={
            "checklist": {
                "media_ready": True,
                "thumbnail_ready": True,
                "title_caption_ready": True,
                "sources_checked": True,
                "asset_rights_verified": True,
            }
        },
    )
    assert patch_checklist_res.status_code == 200
    # Auto-readiness check should transition YouTube to READY!
    assert patch_checklist_res.json()["status"] == "READY"

    # 10. Attempt to mark PUBLISHED without HTTPS post_url -> must fail with 422!
    invalid_pub_res = await client.patch(
        f"/api/v1/publishing/{yt_pub_id}",
        json={"status": "PUBLISHED", "post_url": "http://insecure.url/watch"},
    )
    assert invalid_pub_res.status_code == 422
    assert "HTTPS" in invalid_pub_res.json()["detail"]

    # 11. Mark PUBLISHED with valid HTTPS URL
    valid_pub_res = await client.patch(
        f"/api/v1/publishing/{yt_pub_id}",
        json={
            "status": "PUBLISHED",
            "post_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "platform_post_id": "dQw4w9WgXcQ",
            "notes": "Published to YouTube channel successfully with high engagement.",
        },
    )
    assert valid_pub_res.status_code == 200
    assert valid_pub_res.json()["status"] == "PUBLISHED"
    assert valid_pub_res.json()["published_at"] is not None

    # ContentItem status should now be PARTIALLY_PUBLISHED (since other platforms remain NOT_READY)
    check_item_published = await client.get(f"/api/v1/content-items/{item_id}")
    assert check_item_published.json()["status"] == "PARTIALLY_PUBLISHED"

    # 12. Skip Facebook, Instagram, TikTok -> ContentItem becomes fully PUBLISHED!
    for p_key in ("facebook", "instagram", "tiktok"):
        p_id = platforms_present[p_key]["id"]
        skip_res = await client.patch(
            f"/api/v1/publishing/{p_id}",
            json={"status": "SKIPPED", "notes": "Bypassed for short test."},
        )
        assert skip_res.status_code == 200

    check_item_final = await client.get(f"/api/v1/content-items/{item_id}")
    assert check_item_final.json()["status"] == "PUBLISHED"

    # 13. Verify item appears in publishing list endpoint
    list_res = await client.get("/api/v1/publishing/list")
    assert list_res.status_code == 200
    items_list = list_res.json()
    matching = [it for it in items_list if it["id"] == item_id]
    assert len(matching) == 1
    assert matching[0]["status"] == "PUBLISHED"
    assert matching[0]["platform_statuses"]["youtube"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_export_gate_blocks_without_qc_audit_or_unapproved(client: AsyncClient):
    """Test that even if a script is approved, export is rejected if QC audit is missing or unapproved."""
    test_id = uuid.uuid4().hex[:6]

    # Create family and item
    fam = (await client.post(
        "/api/v1/content-families",
        json={"title": f"QC Gate Family {test_id}", "content_pillar": "Security", "original_value_type": "benchmark"},
    )).json()
    item = (await client.post(
        f"/api/v1/content-families/{fam['id']}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"QC Gate Test {test_id}",
            "angle": "Empirical testing with zero cloud API dependencies.",
            "hook_type": "bold_claim",
            "original_value_connection": "Local benchmark scripts and verified measurements.",
            "viewer_value": "Step by step command tutorial.",
        },
    )).json()

    # Generate script and approve script only
    script = (await client.post("/api/v1/scripts/generate", json={"content_item_id": item["id"]})).json()
    await client.post(f"/api/v1/scripts/{script['id']}/approve", json={"notes": "Script approved"})

    # 1. Attempt export without running QC audit -> rejected 422
    exp_res1 = await client.post(f"/api/v1/export/{item['id']}")
    assert exp_res1.status_code == 422
    assert "No final quality audit found" in exp_res1.json()["detail"]

    # 2. Run QC audit evaluation (leaves status as PENDING / unapproved)
    eval_res = await client.post(f"/api/v1/quality-gate/evaluate/{item['id']}")
    assert eval_res.status_code == 200
    assert eval_res.json()["is_approved"] is False

    # Attempt export with unapproved QC audit -> rejected 422
    exp_res2 = await client.post(f"/api/v1/export/{item['id']}")
    assert exp_res2.status_code == 422
    assert "Final Quality Gate Block" in exp_res2.json()["detail"]


@pytest.mark.asyncio
async def test_export_gate_blocks_stale_qc_audit_after_script_modified(client: AsyncClient, db_session: AsyncSession):
    """Test that modifying a script after QC audit approval invalidates authorization (stale audit)."""
    test_id = uuid.uuid4().hex[:6]

    fam = (await client.post(
        "/api/v1/content-families",
        json={"title": f"Stale QC Family {test_id}", "content_pillar": "Quality", "original_value_type": "benchmark"},
    )).json()
    item = (await client.post(
        f"/api/v1/content-families/{fam['id']}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Stale QC Item {test_id}",
            "angle": "Empirical testing with zero cloud API dependencies.",
            "hook_type": "bold_claim",
            "original_value_connection": "Local benchmark scripts and verified measurements.",
            "viewer_value": "Step by step command tutorial.",
        },
    )).json()

    # Generate and approve script
    script = (await client.post("/api/v1/scripts/generate", json={"content_item_id": item["id"]})).json()
    await client.post(f"/api/v1/scripts/{script['id']}/approve", json={"notes": "Script approved"})

    # Evaluate and approve QC audit
    await client.post(f"/api/v1/quality-gate/evaluate/{item['id']}")
    app_res = await client.post(
        f"/api/v1/quality-gate/approve/{item['id']}",
        json={"approved_by": "Lead Editor", "notes": "Approved"},
    )
    assert app_res.status_code == 200

    # Modify the script (e.g., section refinement or update)
    sec_id = script["sections"][0]["id"]
    refine_res = await client.post(
        f"/api/v1/scripts/{script['id']}/sections/{sec_id}/refine",
        json={"refinement_type": "shorten", "guidance": "Make hook punchier."},
    )
    assert refine_res.status_code == 200

    # Model a persisted edit only 500 ms after QC approval. Any post-approval edit is stale.
    audit = await QualityGateRepository(db_session).get_audit_by_item(item['id'])
    script_record = await db_session.get(ScriptDraft, script['id'])
    assert audit is not None and audit.approved_at is not None
    assert script_record is not None
    script_record.updated_at = audit.approved_at + timedelta(milliseconds=500)
    await db_session.commit()

    # Attempt export -> must be rejected because script was modified after approval
    exp_res = await client.post(f"/api/v1/export/{item['id']}")
    assert exp_res.status_code == 422
    assert "Final Quality Gate Stale Block" in exp_res.json()["detail"]
    assert "modified after final quality gate approval" in exp_res.json()["detail"]

    # Re-evaluating and re-approving QC audit restores ability to export
    await client.post(f"/api/v1/quality-gate/evaluate/{item['id']}")
    reapp_res = await client.post(
        f"/api/v1/quality-gate/approve/{item['id']}",
        json={"approved_by": "Lead Editor", "notes": "Re-approved modified content"},
    )
    assert reapp_res.status_code == 200

    exp_res_ok = await client.post(f"/api/v1/export/{item['id']}")
    assert exp_res_ok.status_code == 200
    assert exp_res_ok.json()["content_item_id"] == item["id"]


@pytest.mark.asyncio
async def test_export_gate_blocks_stale_qc_audit_on_new_script_draft(client: AsyncClient):
    """Test that generating a new script draft supersedes the previous QC audit."""
    test_id = uuid.uuid4().hex[:6]

    fam = (await client.post(
        "/api/v1/content-families",
        json={"title": f"New Script QC Family {test_id}", "content_pillar": "Core", "original_value_type": "benchmark"},
    )).json()
    item = (await client.post(
        f"/api/v1/content-families/{fam['id']}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"New Script QC Item {test_id}",
            "angle": "Empirical testing with zero cloud API dependencies.",
            "hook_type": "bold_claim",
            "original_value_connection": "Local benchmark scripts and verified measurements.",
            "viewer_value": "Step by step command tutorial.",
        },
    )).json()

    # Draft 1
    script1 = (await client.post("/api/v1/scripts/generate", json={"content_item_id": item["id"]})).json()
    await client.post(f"/api/v1/scripts/{script1['id']}/approve", json={"notes": "Script 1 approved"})
    await client.post(f"/api/v1/quality-gate/evaluate/{item['id']}")
    await client.post(f"/api/v1/quality-gate/approve/{item['id']}", json={"approved_by": "Creator"})

    # Draft 2 generated for same item (creates new active script draft)
    script2 = (await client.post("/api/v1/scripts/generate", json={"content_item_id": item["id"]})).json()
    assert script2["id"] != script1["id"]
    await client.post(f"/api/v1/scripts/{script2['id']}/approve", json={"notes": "Script 2 approved"})

    # Export must be blocked because audit was for script 1, not script 2
    exp_res = await client.post(f"/api/v1/export/{item['id']}")
    assert exp_res.status_code == 422
    assert "Final Quality Gate Stale Block" in exp_res.json()["detail"]


@pytest.mark.asyncio
async def test_repeated_export_requests(client: AsyncClient):
    """Test that repeated export requests on an approved item succeed and update the package."""
    test_id = uuid.uuid4().hex[:6]

    fam = (await client.post(
        "/api/v1/content-families",
        json={"title": f"Repeat Export Family {test_id}", "content_pillar": "Core", "original_value_type": "benchmark"},
    )).json()
    item = (await client.post(
        f"/api/v1/content-families/{fam['id']}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Repeat Export Item {test_id}",
            "angle": "Empirical testing with zero cloud API dependencies.",
            "hook_type": "bold_claim",
            "original_value_connection": "Local benchmark scripts and verified measurements.",
            "viewer_value": "Step by step command tutorial.",
        },
    )).json()

    script = (await client.post("/api/v1/scripts/generate", json={"content_item_id": item["id"]})).json()
    await client.post(f"/api/v1/scripts/{script['id']}/approve", json={"notes": "Approved"})
    await client.post(f"/api/v1/quality-gate/evaluate/{item['id']}")
    await client.post(f"/api/v1/quality-gate/approve/{item['id']}", json={"approved_by": "Creator"})

    # First export
    res1 = await client.post(f"/api/v1/export/{item['id']}")
    assert res1.status_code == 200
    pkg1 = res1.json()

    # Repeated export
    res2 = await client.post(f"/api/v1/export/{item['id']}")
    assert res2.status_code == 200
    pkg2 = res2.json()

    assert pkg1["content_item_id"] == pkg2["content_item_id"]
    assert pkg1["id"] == pkg2["id"]
    assert pkg1["package_slug"] == pkg2["package_slug"]
    assert len(pkg2["checksum"]) == 64
    assert pkg1["files"] == pkg2["files"]


