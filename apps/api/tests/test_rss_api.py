import email.utils
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient


def _make_xml(title: str, link: str, summary: str) -> str:
    now = email.utils.format_datetime(datetime.now(timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Mock Source</title>
            <link>https://mock.example.com</link>
            <item>
                <title>{title}</title>
                <link>{link}</link>
                <description>{summary}</description>
                <pubDate>{now}</pubDate>
            </item>
        </channel>
    </rss>"""


@pytest.mark.asyncio
async def test_feed_crud_endpoints(client: AsyncClient):
    # 1. Create Feed
    feed_payload = {
        "name": "OpenAI Engineering Blog",
        "url": "https://openai.com/news/rss.xml",
        "category": "Engineering",
        "trust_weight": 0.95,
        "enabled": True,
    }
    create_res = await client.post("/api/v1/rss/feeds", json=feed_payload)
    assert create_res.status_code == 201
    feed = create_res.json()
    feed_id = feed["id"]
    assert feed["name"] == "OpenAI Engineering Blog"
    assert feed["trust_weight"] == 0.95
    assert feed["failure_count"] == 0

    # 2. Duplicate URL Conflict
    conflict_res = await client.post("/api/v1/rss/feeds", json=feed_payload)
    assert conflict_res.status_code == 409

    # 3. List Feeds
    list_res = await client.get("/api/v1/rss/feeds")
    assert list_res.status_code == 200
    feeds = list_res.json()
    assert any(f["id"] == feed_id for f in feeds)

    # 4. Update Feed
    update_res = await client.put(
        f"/api/v1/rss/feeds/{feed_id}",
        json={"category": "Core AI Research", "trust_weight": 0.98},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["category"] == "Core AI Research"
    assert updated["trust_weight"] == 0.98

    # 5. Delete Feed
    del_res = await client.delete(f"/api/v1/rss/feeds/{feed_id}")
    assert del_res.status_code == 204

    # 6. Verify Deleted
    get_res = await client.get(f"/api/v1/rss/feeds/{feed_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_rss_run_and_dry_run_api(client: AsyncClient):
    # Create a test feed
    feed_url = "https://agenttesting.example.com/rss.xml"
    feed_payload = {
        "name": "Agent Testing Daily",
        "url": feed_url,
        "category": "Testing",
        "trust_weight": 0.9,
        "enabled": True,
    }
    await client.post("/api/v1/rss/feeds", json=feed_payload)

    xml = _make_xml(
        title="Coding Agent Benchmark Evaluation on Dirty Codebases",
        link="https://agenttesting.example.com/article-1?utm_source=rss",
        summary="Stress testing autonomous coding agents on Python and TypeScript repositories with reproducible benchmark and code repository.",
    )

    # 1. Dry Run
    dry_res = await client.post(
        "/api/v1/rss/dry-run",
        json={"xml_fixtures": {feed_url: xml}},
    )
    assert dry_res.status_code == 200
    dry_data = dry_res.json()
    assert dry_data["engine_result"]["output_count"] == 1
    assert "Coding Agent" in dry_data["engine_result"]["outputs"][0]["title"]

    # 2. Real Run
    run_res = await client.post(
        "/api/v1/rss/run",
        json={"xml_fixtures": {feed_url: xml}},
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["engine_result"]["success"] is True
    assert run_data["engine_result"]["output_count"] == 1

    # 3. List candidates endpoint
    cand_res = await client.get("/api/v1/rss/candidates?in_niche_only=true")
    assert cand_res.status_code == 200
    candidates = cand_res.json()
    assert len(candidates) >= 1
    candidate_id = candidates[0]["id"]

    # 4. Get candidate details
    detail_res = await client.get(f"/api/v1/rss/candidates/{candidate_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == candidate_id
    assert detail["source_count"] >= 1
    assert detail["is_in_niche"] is True
