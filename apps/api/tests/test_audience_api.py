import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.content_family import ContentItem, ContentFamily


@pytest.mark.asyncio
async def test_audience_full_api_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup a test Content Item for attribution
    family = ContentFamily(
        id=str(uuid.uuid4()),
        title="Audience Growth Masterclass",
        slug=f"audience-growth-{uuid.uuid4().hex[:6]}",
        status="ACTIVE",
    )
    db_session.add(family)
    await db_session.flush()

    item = ContentItem(
        id=str(uuid.uuid4()),
        content_family_id=family.id,
        format="long_video",
        platform_target="youtube",
        working_title="How to Build 10,000 Owned Subscribers",
        angle="Actionable blueprint converting views into email leads",
        status="PUBLISHED",
    )
    db_session.add(item)
    await db_session.commit()

    # 2. Create Lead Magnet
    slug = f"ai-cheatsheet-{uuid.uuid4().hex[:6]}"
    create_payload = {
        "title": "Ultimate AI Architecture Cheatsheet",
        "slug": slug,
        "description": "Comprehensive reference PDF with 15 architecture patterns.",
        "magnet_type": "cheat_sheet",
        "landing_page_url": f"https://example.com/resources/{slug}",
        "cta_copy": "Grab the free cheat sheet: {url}",
        "status": "ACTIVE",
        "target_pillar": "Architecture",
        "estimated_value_usd": 20.0,
    }
    mag_res = await client.post("/api/v1/audience/magnets", json=create_payload)
    assert mag_res.status_code == 201
    mag_data = mag_res.json()
    magnet_id = mag_data["id"]
    assert mag_data["title"] == create_payload["title"]
    assert mag_data["slug"] == slug
    assert mag_data["estimated_value_usd"] == 20.0

    # Test duplicate slug rejection
    dup_res = await client.post("/api/v1/audience/magnets", json=create_payload)
    assert dup_res.status_code == 400

    # 3. List Lead Magnets
    list_res = await client.get("/api/v1/audience/magnets?status=ACTIVE")
    assert list_res.status_code == 200
    magnets_list = list_res.json()
    assert any(m["id"] == magnet_id for m in magnets_list)

    # 4. Get Lead Magnet by ID
    get_res = await client.get(f"/api/v1/audience/magnets/{magnet_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == magnet_id

    # 5. Update Lead Magnet
    update_res = await client.put(
        f"/api/v1/audience/magnets/{magnet_id}",
        json={"estimated_value_usd": 25.0, "target_pillar": "Deep Tech"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["estimated_value_usd"] == 25.0
    assert update_res.json()["target_pillar"] == "Deep Tech"

    # 6. Build UTM Tracking Link
    utm_req = {
        "base_url": create_payload["landing_page_url"],
        "platform": "youtube",
        "lead_magnet_slug": slug,
        "content_slug": "youtube-10k-subscribers",
        "campaign_name": "growth_series",
    }
    utm_res = await client.post("/api/v1/audience/build-utm", json=utm_req)
    assert utm_res.status_code == 200
    utm_data = utm_res.json()
    assert "utm_source=youtube" in utm_data["tracking_url"]
    assert "utm_campaign=sc_growth_series" in utm_data["tracking_url"]
    assert utm_data["tracking_url"] in utm_data["copy_paste_cta"]

    # 7. Record Conversion Snapshot
    conv_payload = {
        "lead_magnet_id": magnet_id,
        "content_item_id": item.id,
        "platform": "youtube",
        "utm_source": "youtube",
        "utm_medium": "video_description",
        "utm_campaign": "sc_growth_series",
        "clicks": 150,
        "signups": 15,
        "customers": 2,
        "revenue_usd": 99.0,
        "notes": "Strong conversion from long-form video CTA card",
        "source": "MANUAL",
    }
    conv_res = await client.post("/api/v1/audience/conversions", json=conv_payload)
    assert conv_res.status_code == 201
    conv_data = conv_res.json()
    assert conv_data["clicks"] == 150
    assert conv_data["signups"] == 15
    assert conv_data["conversion_rate_pct"] == 10.0
    assert conv_data["lead_magnet_title"] == "Ultimate AI Architecture Cheatsheet"
    assert conv_data["content_item_title"] == "How to Build 10,000 Owned Subscribers"

    # 8. List Conversions
    list_conv = await client.get(f"/api/v1/audience/conversions?lead_magnet_id={magnet_id}")
    assert list_conv.status_code == 200
    conversions_list = list_conv.json()
    assert len(conversions_list) >= 1
    assert conversions_list[0]["lead_magnet_id"] == magnet_id

    # 9. Verify Lead Magnet computed metrics reflect conversion
    updated_mag = await client.get(f"/api/v1/audience/magnets/{magnet_id}")
    assert updated_mag.status_code == 200
    mag_metrics = updated_mag.json()
    assert mag_metrics["total_clicks"] >= 150
    assert mag_metrics["total_signups"] >= 15
    assert mag_metrics["conversion_rate_pct"] == 10.0
    assert mag_metrics["estimated_asset_value_usd"] == 15 * 25.0

    # 10. Audience Summary
    sum_res = await client.get("/api/v1/audience/summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert sum_data["total_lead_magnets"] >= 1
    assert sum_data["total_clicks"] >= 150
    assert sum_data["total_signups"] >= 15
    assert sum_data["estimated_total_list_value_usd"] >= 375.0
    assert "youtube" in sum_data["by_platform"]

    # 11. Audience Economics Explanation
    exp_res = await client.get("/api/v1/audience/explain")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert len(exp_data["factors"]) == 3
    assert "economics_breakdown" in exp_data

    # 12. Delete Lead Magnet
    del_res = await client.delete(f"/api/v1/audience/magnets/{magnet_id}")
    assert del_res.status_code == 204

    # Confirm 404 after deletion
    del_check = await client.get(f"/api/v1/audience/magnets/{magnet_id}")
    assert del_check.status_code == 404
