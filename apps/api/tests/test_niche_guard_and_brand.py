import pytest
from httpx import AsyncClient
from app.engines.core.registry import engine_registry
from app.engines.niche_guard.engine import NicheGuardEngine
from app.engines.brand.engine import BrandEngine


@pytest.mark.asyncio
async def test_niche_guard_engine_registration():
    engine = engine_registry.get("niche_guard")
    assert engine is not None
    assert isinstance(engine, NicheGuardEngine)
    assert engine.id == "niche_guard"
    assert engine.health().status == "healthy"


@pytest.mark.asyncio
async def test_brand_engine_registration():
    engine = engine_registry.get("brand")
    assert engine is not None
    assert isinstance(engine, BrandEngine)
    assert engine.id == "brand"
    assert engine.health().status == "healthy"


@pytest.mark.asyncio
async def test_niche_guard_api_in_niche(client: AsyncClient):
    payload = {
        "title": "Stress-Testing Coding Agents on Dirty Legacy Codebases",
        "text": "Empirical comparison measuring latency and token costs with local LLMs and IDE integrations. Full code repository and reproducible benchmark data provided.",
        "tags": ["coding agents", "local LLMs", "evals and benchmarks"],
    }
    resp = await client.post("/api/v1/niche-guard/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["passed"] is True
    assert data["score"] >= 55.0
    assert len(data["matched_allowed_topics"]) > 0
    assert len(data["pillar_matches"]) > 0
    assert len(data["blocked_topics_detected"]) == 0
    assert "Approved" in data["reason"]


@pytest.mark.asyncio
async def test_niche_guard_api_blocked_topic(client: AsyncClient):
    payload = {
        "title": "Passive income schemes with crypto/web3 trading",
        "text": "Fast money algorithms for trading.",
        "tags": ["trading"],
    }
    resp = await client.post("/api/v1/niche-guard/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["passed"] is False
    assert data["score"] == 0.0
    assert len(data["blocked_topics_detected"]) > 0
    assert "Rejected" in data["reason"]
    assert "blocked topic detected" in data["reason"]


@pytest.mark.asyncio
async def test_niche_guard_api_off_niche(client: AsyncClient):
    payload = {
        "title": "Beginner Guide to Baking Crusty Sourdough Boules",
        "text": "Flour, water, salt, and fermentation techniques for artisan sourdough bread.",
        "tags": ["baking", "sourdough"],
    }
    resp = await client.post("/api/v1/niche-guard/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["passed"] is False
    assert data["score"] < 55.0
    assert "Rejected" in data["reason"]


@pytest.mark.asyncio
async def test_brand_qa_api_on_brand(client: AsyncClient):
    payload = {
        "title": "Local Qwen 2.5 Coder Benchmark",
        "body": "In this benchmark, we measured latency and failure rate across local workflows. The trade-off is clear when comparing reproducible tokens per second.",
        "hook": "Here is what happens when you run coding benchmarks locally.",
        "cta": "Inspect the reproduction script linked below.",
        "platform": "youtube_shorts",
    }
    resp = await client.post("/api/v1/brand-qa/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["on_brand"] is True
    assert data["overall_score"] >= 70.0
    assert len(data["matched_preferred_words"]) >= 2
    assert len(data["matched_avoid_words"]) == 0
    assert len(data["matched_cliches"]) == 0
    assert not any(v["severity"] == "critical" for v in data["violations"])


@pytest.mark.asyncio
async def test_brand_qa_api_banned_cliche(client: AsyncClient):
    payload = {
        "title": "Future of AI",
        "body": "In today's fast-paced world, without further ado, let's dive right in and explore how AI is evolving.",
        "hook": "Let's dive right in!",
    }
    resp = await client.post("/api/v1/brand-qa/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["on_brand"] is False
    assert len(data["matched_cliches"]) >= 2
    assert any(v["rule_type"] == "banned_cliche" for v in data["violations"])
    assert len(data["suggested_fixes"]) > 0


@pytest.mark.asyncio
async def test_brand_qa_api_avoid_vocabulary(client: AsyncClient):
    payload = {
        "title": "Crazy AI Breakthrough",
        "body": "This mind-blowing tool is an insane game-changer for passive income! Unbelievable results!",
    }
    resp = await client.post("/api/v1/brand-qa/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["on_brand"] is False
    assert len(data["matched_avoid_words"]) >= 3
    assert any(v["rule_type"] == "avoid_vocabulary" for v in data["violations"])


@pytest.mark.asyncio
async def test_engine_registry_execution_and_audit(client: AsyncClient):
    # Test executing niche_guard and brand via the general engines API
    resp_ng = await client.post("/api/v1/engines/niche_guard/run", json={"trigger": "manual"})
    assert resp_ng.status_code == 200
    ng_data = resp_ng.json()
    assert ng_data["success"] is True
    assert ng_data["engine_id"] == "niche_guard"

    resp_brand = await client.post("/api/v1/engines/brand/run", json={"trigger": "manual"})
    assert resp_brand.status_code == 200
    brand_data = resp_brand.json()
    assert brand_data["success"] is True
    assert brand_data["engine_id"] == "brand"

    # Verify runs are logged in audit endpoint
    runs_ng = await client.get("/api/v1/engines/niche_guard/runs?limit=10")
    assert runs_ng.status_code == 200
    assert len(runs_ng.json()) >= 1
    assert runs_ng.json()[0]["engine_id"] == "niche_guard"

    runs_brand = await client.get("/api/v1/engines/brand/runs?limit=10")
    assert runs_brand.status_code == 200
    assert len(runs_brand.json()) >= 1
    assert runs_brand.json()[0]["engine_id"] == "brand"
