import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_opportunity_api_lifecycle(client: AsyncClient):
    test_id = uuid.uuid4().hex[:8]

    # 1. Run Opportunity Engine with custom seed topic
    run_payload = {
        "custom_topics": [
            {
                "topic": f"Local DeepSeek Inference on Mac M4 Max {test_id}",
                "summary": "Benchmarking token generation speed, unified memory saturation, and power efficiency.",
                "pillar": "Hardware Benchmarks",
                "trend_score": 88.0,
            }
        ],
        "include_candidates": False,
        "include_trends": False,
    }
    run_res = await client.post("/api/v1/opportunities/run", json=run_payload)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["success"] is True
    assert run_data["output_count"] >= 1

    # 2. List Opportunities
    list_res = await client.get("/api/v1/opportunities?sort_by=opportunity_score&limit=20")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1

    matching = next((o for o in items if test_id in o["topic"]), None)
    assert matching is not None
    opp_id = matching["id"]
    assert matching["status"] == "needs_review"
    assert matching["opportunity_score"] > 0.0
    assert matching["suggested_original_angle"] != ""

    # 3. Get Single Opportunity Detail
    detail_res = await client.get(f"/api/v1/opportunities/{opp_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == opp_id
    assert "score_breakdown" in detail

    # 4. Explain Opportunity
    explain_res = await client.get(f"/api/v1/opportunities/{opp_id}/explain")
    assert explain_res.status_code == 200
    expl = explain_res.json()
    assert "summary" in expl

    # 5. Human Gate Action: Watch
    watch_res = await client.post(f"/api/v1/opportunities/{opp_id}/watch")
    assert watch_res.status_code == 200
    watched = watch_res.json()
    assert watched["status"] == "watching"

    # 6. Human Gate Action: Approve for Research
    research_res = await client.post(f"/api/v1/opportunities/{opp_id}/research")
    assert research_res.status_code == 200
    approved = research_res.json()
    assert approved["status"] == "research_ready"

    # 7. Human Gate Action: Reject
    reject_res = await client.post(
        f"/api/v1/opportunities/{opp_id}/reject",
        json={"rejection_reason": "Device unavailable in lab"},
    )
    assert reject_res.status_code == 200
    rejected = reject_res.json()
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "Device unavailable in lab"

    # 8. Creator Cockpit Summary
    cockpit_res = await client.get("/api/v1/opportunities/cockpit/summary")
    assert cockpit_res.status_code == 200
    summary = cockpit_res.json()
    assert "signals_today" in summary
    assert "needs_review" in summary
    assert "research_ready" in summary
    assert "ai_spend" in summary
    assert "disk_usage" in summary
    assert "engine_health_summary" in summary
    assert len(summary["engine_health_summary"]) >= 4  # niche_guard, brand, rss, trends, opportunity
