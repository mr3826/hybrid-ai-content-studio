import email.utils
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.rss.adapters import canonicalize_url
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.rss import DiscoveredCandidate


_TEST_NICHE: dict[str, Any] = {
    "name": "RSS API Fixture Niche",
    "one_sentence_definition": "Engineering evaluation of coding agents and reproducible benchmarks.",
    "audience": "Software engineers evaluating practical coding agent tools.",
    "audience_regions": ["Global"],
    "primary_problems": ["coding agent benchmark evaluation"],
    "allowed_topics": ["coding agent", "benchmark", "Python", "TypeScript"],
    "adjacent_topics": [],
    "blocked_topics": [],
    "must_have_signals": [],
    "negative_keywords": [],
    "preferred_source_types": ["engineering"],
    "content_pillars": [
        {"name": "Coding Agent Evaluation", "keywords": ["coding agent", "benchmark"]}
    ],
    "commercial_intent_topics": [],
    "evergreen_topics": [],
}
_TEST_NICHE_FIELDS = tuple(_TEST_NICHE)


@asynccontextmanager
async def _temporary_test_niche(
    db_session: AsyncSession,
) -> AsyncIterator[dict[str, Any] | None]:
    """Install a deterministic niche for this API test and restore shared state."""
    niche = await db_session.get(NicheProfile, SINGLETON_NICHE_ID)
    previous = (
        {field: deepcopy(getattr(niche, field)) for field in _TEST_NICHE_FIELDS}
        if niche is not None
        else None
    )

    if niche is None:
        niche = NicheProfile(id=SINGLETON_NICHE_ID, **deepcopy(_TEST_NICHE))
        db_session.add(niche)
    else:
        for field, value in _TEST_NICHE.items():
            setattr(niche, field, deepcopy(value))
    await db_session.commit()

    try:
        yield previous
    finally:
        niche = await db_session.get(NicheProfile, SINGLETON_NICHE_ID)
        if previous is None:
            if niche is not None:
                await db_session.delete(niche)
        elif niche is None:
            db_session.add(NicheProfile(id=SINGLETON_NICHE_ID, **deepcopy(previous)))
        else:
            for field, value in previous.items():
                setattr(niche, field, deepcopy(value))
        await db_session.commit()


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
    # 1. Create Feed. Unique values avoid collisions with retained local test data.
    token = uuid4().hex
    feed_payload = {
        "name": f"OpenAI Engineering Blog {token}",
        "url": f"https://openai.com/news/{token}/rss.xml",
        "category": "Engineering",
        "trust_weight": 0.95,
        "enabled": True,
    }
    create_res = await client.post("/api/v1/rss/feeds", json=feed_payload)
    assert create_res.status_code == 201
    feed = create_res.json()
    feed_id = feed["id"]
    assert feed["name"] == feed_payload["name"]
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
async def test_rss_run_and_dry_run_api(client: AsyncClient, db_session: AsyncSession):
    token = uuid4().hex
    feed_url = f"https://rss-api-{token}.example.com/rss.xml"
    article_url = f"https://rss-api.example.com/articles/{token}"
    title = f"Coding Agent RSS API Fixture {token}"
    summary = (
        f"Fixture {token} reports a reproducible benchmark evaluating coding agent tools "
        "on Python and TypeScript repositories."
    )
    xml = _make_xml(title=title, link=article_url, summary=summary)
    feed_payload = {
        "name": f"RSS API Fixture {token}",
        "url": feed_url,
        "category": "Testing",
        "trust_weight": 0.9,
        "enabled": True,
    }
    created_feed_id: str | None = None

    async with _temporary_test_niche(db_session) as previous_niche:
        try:
            create_res = await client.post("/api/v1/rss/feeds", json=feed_payload)
            assert create_res.status_code == 201
            created_feed_id = create_res.json()["id"]
            feeds = [
                {
                    "id": created_feed_id,
                    "name": feed_payload["name"],
                    "url": feed_url,
                    "category": "Testing",
                    "trust_weight": 0.9,
                    "enabled": True,
                }
            ]
            parameters = {"feeds": feeds, "xml_fixtures": {feed_url: xml}}

            # 1. Dry Run
            dry_res = await client.post("/api/v1/rss/dry-run", json=parameters)
            assert dry_res.status_code == 200
            dry_data = dry_res.json()
            assert dry_data["engine_result"]["output_count"] == 1
            assert dry_data["engine_result"]["outputs"][0]["title"] == title

            # 2. Real Run
            run_res = await client.post("/api/v1/rss/run", json=parameters)
            assert run_res.status_code == 200
            run_data = run_res.json()
            assert run_data["engine_result"]["success"] is True
            assert run_data["engine_result"]["output_count"] == 1

            # 3. List candidates and select this fixture by its source URL, never by list order.
            cand_res = await client.get(
                "/api/v1/rss/candidates?in_niche_only=true&limit=200"
            )
            assert cand_res.status_code == 200
            candidates = cand_res.json()
            matching = [
                candidate
                for candidate in candidates
                if any(source.get("url") == article_url for source in candidate["sources"])
            ]
            assert len(matching) == 1
            candidate = matching[0]
            candidate_id = candidate["id"]
            assert candidate["title"] == title
            assert candidate["is_in_niche"] is True

            # 4. Get candidate details
            detail_res = await client.get(f"/api/v1/rss/candidates/{candidate_id}")
            assert detail_res.status_code == 200
            detail = detail_res.json()
            assert detail["id"] == candidate_id
            assert detail["source_count"] == 1
            assert detail["is_in_niche"] is True
        finally:
            # The API run persists its candidate; remove only this test's unique record.
            await db_session.execute(
                delete(DiscoveredCandidate).where(
                    DiscoveredCandidate.canonical_url == canonicalize_url(article_url)
                )
            )
            await db_session.commit()
            if created_feed_id is not None:
                delete_res = await client.delete(f"/api/v1/rss/feeds/{created_feed_id}")
                assert delete_res.status_code == 204

    restored_niche = await db_session.get(NicheProfile, SINGLETON_NICHE_ID)
    if previous_niche is None:
        assert restored_niche is None
    else:
        assert restored_niche is not None
        assert {
            field: getattr(restored_niche, field) for field in _TEST_NICHE_FIELDS
        } == previous_niche
