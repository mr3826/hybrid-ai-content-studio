import uuid
from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_analytics_api_full_flow(client: AsyncClient):
    test_id = uuid.uuid4().hex[:6]

    # 1. Create content family and item
    fam_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Analytics Family ({test_id})",
            "content_pillar": "Performance Testing",
            "original_value_type": "benchmark",
            "summary": "Analytics integration testing.",
        },
    )
    assert fam_res.status_code == 201
    family_id = fam_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Analytics Target ({test_id})",
            "angle": "Measuring retention and revenue.",
            "hook_type": "bold_claim",
            "original_value_connection": "Verified analytics measurements.",
            "viewer_value": "Actionable analytics formulas.",
        },
    )
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    # Generate script so hook text is available
    await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id},
    )

    # 2. Record manual snapshot (24h)
    snap_res = await client.post(
        "/api/v1/analytics/snapshots",
        json={
            "content_item_id": item_id,
            "platform": "youtube",
            "snapshot_label": "24h",
            "views": 2500,
            "impressions": 15000,
            "watch_time_seconds": 9500.0,
            "average_view_duration_seconds": 38.0,
            "retention_rate_pct": 68.5,
            "hook_retention_3s_pct": 78.0,
            "hook_retention_30s_pct": 52.0,
            "likes": 180,
            "comments": 25,
            "shares": 15,
            "saves": 20,
            "clicks": 45,
            "subscribers_gained": 35,
            "revenue_estimated_usd": 32.50,
            "notes": "First 24 hours performing strongly.",
        },
    )
    assert snap_res.status_code == 201
    snap_data = snap_res.json()
    snap_id = snap_data["id"]
    assert snap_data["content_item_id"] == item_id
    assert snap_data["platform"] == "youtube"
    assert snap_data["views"] == 2500
    assert snap_data["engagement_rate_pct"] > 0

    # 3. Record follow-up snapshot (7d)
    snap7_res = await client.post(
        "/api/v1/analytics/snapshots",
        json={
            "content_item_id": item_id,
            "platform": "youtube",
            "snapshot_label": "7d",
            "views": 8500,
            "impressions": 48000,
            "watch_time_seconds": 31000.0,
            "average_view_duration_seconds": 36.5,
            "retention_rate_pct": 64.0,
            "hook_retention_3s_pct": 78.0,
            "hook_retention_30s_pct": 50.0,
            "likes": 560,
            "comments": 78,
            "shares": 42,
            "saves": 65,
            "clicks": 140,
            "subscribers_gained": 95,
            "revenue_estimated_usd": 110.0,
            "notes": "7 days algorithmic push.",
        },
    )
    assert snap7_res.status_code == 201

    # 4. List snapshots
    list_res = await client.get(f"/api/v1/analytics/snapshots?content_item_id={item_id}")
    assert list_res.status_code == 200
    snapshots_list = list_res.json()
    assert len(snapshots_list) == 2

    # 5. Get snapshot by ID
    get_res = await client.get(f"/api/v1/analytics/snapshots/{snap_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == snap_id

    # 6. Get item analytics & ROI
    item_analytics_res = await client.get(f"/api/v1/analytics/item/{item_id}")
    assert item_analytics_res.status_code == 200
    item_analytics = item_analytics_res.json()
    assert item_analytics["total_snapshots"] == 2
    assert item_analytics["total_views"] == 11000
    assert item_analytics["total_revenue_usd"] == 142.50
    assert "roi_analysis" in item_analytics
    assert item_analytics["roi_analysis"]["total_revenue_usd"] == 142.50

    # 7. Get studio performance summary
    summary_res = await client.get("/api/v1/analytics/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_snapshots"] >= 2
    assert summary["total_views"] >= 11000
    assert len(summary["platforms"]) >= 1

    # 8. Get hook retention rankings
    hooks_res = await client.get("/api/v1/analytics/hooks")
    assert hooks_res.status_code == 200
    hooks = hooks_res.json()
    assert len(hooks) >= 1
    assert any(h["content_item_id"] == item_id for h in hooks)

    # 9. Test CSV import
    csv_body = f"""content_item_id,platform,snapshot_label,views,likes,comments,shares,revenue_estimated_usd,hook_retention_3s_pct
{item_id},tiktok,24h,4200,280,35,22,12.50,81.5
"""
    csv_res = await client.post(
        "/api/v1/analytics/import-csv",
        json={"csv_content": csv_body},
    )
    assert csv_res.status_code == 200
    csv_data = csv_res.json()
    assert csv_data["imported_count"] == 1
    assert csv_data["failed_count"] == 0

    # 10. Run analytics engine batch execution
    run_res = await client.post("/api/v1/analytics/run-engine", json={})
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["success"] is True

    # 11. Delete first snapshot
    del_res = await client.delete(f"/api/v1/analytics/snapshots/{snap_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
