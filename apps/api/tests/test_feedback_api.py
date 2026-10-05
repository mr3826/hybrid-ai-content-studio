import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.content_family import ContentItem, ContentFamily
from app.models.script import ScriptDraft, ScriptSection
from app.models.analytics import PublicationMetricsSnapshot
from app.models.brand import BrandProfile, SINGLETON_BRAND_ID
from sqlalchemy import select


@pytest.mark.asyncio
async def test_feedback_full_api_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 0. Setup Brand Profile
    brand_stmt = select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID)
    brand_res = await db_session.execute(brand_stmt)
    brand = brand_res.scalar_one_or_none()
    if not brand:
        brand = BrandProfile(
            id=SINGLETON_BRAND_ID,
            brand_name="Tech Brand",
            brand_promise="Tested Insights",
            audience="Engineers",
            avoid_vocabulary=["cliche_one"],
            preferred_vocabulary=["concrete"],
            banned_cliches=["game changer"],
        )
        db_session.add(brand)
        await db_session.commit()

    # 1. Setup Content Item and Script
    family = ContentFamily(
        id=str(uuid.uuid4()),
        title="Async Python Studio",
        slug=f"async-python-{uuid.uuid4().hex[:6]}",
        status="ACTIVE",
    )
    db_session.add(family)
    await db_session.flush()

    item = ContentItem(
        id=str(uuid.uuid4()),
        content_family_id=family.id,
        format="short_vertical",
        platform_target="tiktok",
        working_title="Stop using raw threads",
        angle="Empirical comparison between threads and asyncio",
        status="PUBLISHED",
    )
    db_session.add(item)
    await db_session.flush()

    script = ScriptDraft(
        id=str(uuid.uuid4()),
        content_item_id=item.id,
        version=1,
        format="short_vertical",
        title="Stop using raw threads",
    )
    db_session.add(script)
    await db_session.flush()

    hook_sec = ScriptSection(
        id=str(uuid.uuid4()),
        script_id=script.id,
        order_index=1,
        section_type="hook",
        narration="Hey guys welcome back to the channel today we talk about asyncio",
        estimated_seconds=4,
    )
    db_session.add(hook_sec)
    await db_session.flush()

    # 2. Setup Snapshots: one with hook drop (< 45%), one with high viral retention (> 75%)
    snap_low = PublicationMetricsSnapshot(
        id=str(uuid.uuid4()),
        content_item_id=item.id,
        platform="tiktok",
        views=300,
        impressions=1200,
        hook_retention_3s_pct=25.0,
        retention_rate_pct=18.0,
        likes=5,
        comments=1,
        shares=0,
        saves=0,
    )
    db_session.add(snap_low)
    await db_session.commit()

    # 3. Initial summary check
    sum_res = await client.get("/api/v1/feedback/summary")
    assert sum_res.status_code == 200
    initial_summary = sum_res.json()
    assert "total_lessons" in initial_summary

    # 4. Trigger Evaluate: Synthesizes performance feedback
    eval_res = await client.post("/api/v1/feedback/evaluate", json={"days": 30, "min_impressions": 50})
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["evaluated_snapshots"] >= 1
    assert eval_data["lessons_generated"] >= 1
    assert len(eval_data["lessons"]) >= 1

    generated_lesson = eval_data["lessons"][0]
    lesson_id = generated_lesson["id"]
    assert generated_lesson["status"] == "PENDING"

    # 5. List lessons
    list_res = await client.get("/api/v1/feedback/lessons?status=PENDING")
    assert list_res.status_code == 200
    pending_list = list_res.json()
    assert any(l["id"] == lesson_id for l in pending_list)

    # 6. Explain lesson
    explain_res = await client.get(f"/api/v1/feedback/explain/{lesson_id}")
    assert explain_res.status_code == 200
    explain_data = explain_res.json()
    assert explain_data["human_gate_required"] is True

    # 7. Approve lesson (Creator Gate)
    appr_res = await client.post(
        f"/api/v1/feedback/lessons/{lesson_id}/approve",
        json={"creator_notes": "Agreed, we must ban 'hey guys' and tighten TikTok hooks"},
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "APPROVED"
    assert appr_data["creator_notes"] == "Agreed, we must ban 'hey guys' and tighten TikTok hooks"

    # 8. Apply lesson to Brand DNA
    apply_res = await client.post(f"/api/v1/feedback/lessons/{lesson_id}/apply")
    assert apply_res.status_code == 200
    applied_data = apply_res.json()
    assert applied_data["status"] == "APPLIED"
    assert applied_data["applied_at"] is not None

    # Verify Brand Profile was updated
    db_session.expire_all()
    brand_check = await db_session.execute(select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID))
    refreshed_brand = brand_check.scalar_one()
    # Check if avoid_vocabulary or brand_memory received the value
    target = applied_data["proposed_adjustment"].get("target")
    if target == "brand_profile":
        field = applied_data["proposed_adjustment"].get("field")
        val = applied_data["proposed_adjustment"].get("value")
        current_list = getattr(refreshed_brand, field, [])
        assert val in current_list

    # 9. Manual Lesson Creation & Rejection flow
    manual_payload = {
        "lesson_type": "banned_phrase_addition",
        "title": "Ban 'Game Changer' from all script hooks",
        "observation": "Audience comments flagged that 'game changer' sounds spammy.",
        "impact_level": "HIGH",
        "confidence_score": 0.95,
        "evidence_data": {"source": "creator_observation"},
        "proposed_adjustment": {
            "target": "brand_profile",
            "field": "banned_cliches",
            "action": "append",
            "value": "game changer",
            "summary": "Add to banned cliches",
        },
    }
    man_res = await client.post("/api/v1/feedback/lessons", json=manual_payload)
    assert man_res.status_code == 201
    man_data = man_res.json()
    man_id = man_data["id"]

    # Reject manual lesson
    rej_res = await client.post(
        f"/api/v1/feedback/lessons/{man_id}/reject",
        json={"creator_notes": "Not needed right now, already covered."},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"

    # Cannot apply rejected lesson
    rej_apply = await client.post(f"/api/v1/feedback/lessons/{man_id}/apply")
    assert rej_apply.status_code == 400

    # 10. Summary Verification
    final_sum_res = await client.get("/api/v1/feedback/summary")
    assert final_sum_res.status_code == 200
    final_sum = final_sum_res.json()
    assert final_sum["applied_count"] >= 1
    assert final_sum["rejected_count"] >= 1
