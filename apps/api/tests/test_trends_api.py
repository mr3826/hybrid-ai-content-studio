from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trends_api_lifecycle(client: AsyncClient):
    # 1. Post a manual signal to seed trend momentum
    signal_payload = {
        "title": "DeepSeek R1 Architecture Deep Dive",
        "source_name": "AI Research Today",
        "summary": "Comprehensive architectural breakdown of reasoning and reinforcement learning techniques in DeepSeek R1.",
        "url": "https://example.com/deepseek-r1-analysis",
        "pillar": "AI Architecture",
        "trust_weight": 0.92,
    }
    signal_res = await client.post("/api/v1/trends/manual-signal", json=signal_payload)
    assert signal_res.status_code == 200
    topic = signal_res.json()
    topic_id = topic["id"]
    assert "DeepSeek" in topic["title"] or "deepseek" in topic["topic_key"]
    assert topic["trend_score"] > 0.0

    # 2. Get Trend Topic Detail
    detail_res = await client.get(f"/api/v1/trends/{topic_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == topic_id
    assert "history" in detail
    assert len(detail["history"]) >= 1

    # 3. Get Explainability Breakdown
    explain_res = await client.get(f"/api/v1/trends/{topic_id}/explain")
    assert explain_res.status_code == 200
    expl = explain_res.json()
    assert "summary" in expl
    assert "mention" in expl["summary"].lower()

    # 4. List Trends with Filter
    list_res = await client.get("/api/v1/trends?sort_by=trend_score&limit=10")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(t["id"] == topic_id for t in items)

    # 5. Apply Manual Boost (+25%)
    initial_score = topic["trend_score"]
    boost_res = await client.post(f"/api/v1/trends/{topic_id}/boost", json={"boost_factor": 1.25})
    assert boost_res.status_code == 200
    boosted = boost_res.json()
    assert boosted["manual_boost"] == 1.25
    assert boosted["trend_score"] >= initial_score

    # 6. Toggle Manual Suppress
    suppress_res = await client.post(f"/api/v1/trends/{topic_id}/suppress", json={"suppress": True})
    assert suppress_res.status_code == 200
    suppressed = suppress_res.json()
    assert suppressed["is_suppressed"] is True
    assert suppressed["trend_score"] == 0.0
    assert suppressed["status"] == "archived"

    # Restore from suppression
    restore_res = await client.post(f"/api/v1/trends/{topic_id}/suppress", json={"suppress": False})
    assert restore_res.status_code == 200
    restored = restore_res.json()
    assert restored["is_suppressed"] is False
    assert restored["trend_score"] > 0.0

    # 7. Dry-Run Execution
    dry_res = await client.post("/api/v1/trends/dry-run")
    assert dry_res.status_code == 200
    dry_data = dry_res.json()
    assert dry_data["success"] is True

    # 8. Full Run Execution
    run_res = await client.post("/api/v1/trends/run")
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["success"] is True
