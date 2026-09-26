import pytest
from httpx import AsyncClient

SAMPLE_NICHE_PAYLOAD = {
    "name": "AI Engineering & Coding Automation",
    "one_sentence_definition": "Practical AI coding agents, developer automation workflows, and local LLM tooling tested on production tasks.",
    "audience": "Software developers, technical founders, and automation engineers.",
    "audience_regions": ["North America", "Europe"],
    "primary_problems": [
        "Agent benchmark claims do not match real-world performance.",
        "High API costs and token limits.",
    ],
    "allowed_topics": ["coding agents", "local LLMs", "developer tools"],
    "adjacent_topics": ["software architecture", "DevOps"],
    "blocked_topics": ["crypto/web3 trading", "get rich quick"],
    "must_have_signals": ["code repository", "reproducible benchmark"],
    "negative_keywords": ["secret trick", "replaced all coders"],
    "preferred_source_types": ["github_releases", "engineering_blogs"],
    "content_pillars": [
        {
            "id": "agent_benchmarks",
            "name": "Coding Agent Stress Tests",
            "description": "Real-world testing of Claude 3.7, Gemini 2.5 on dirty repos.",
        }
    ],
    "commercial_intent_topics": ["developer productivity tools"],
    "evergreen_topics": ["how to evaluate LLM code quality"],
}


@pytest.mark.asyncio
async def test_niche_lifecycle_and_singleton_invariant(client: AsyncClient):
    # 1. Update/Create active niche
    res = await client.put("/api/v1/niche", json=SAMPLE_NICHE_PAYLOAD)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "primary"
    assert data["name"] == "AI Engineering & Coding Automation"
    assert len(data["content_pillars"]) == 1
    assert data["content_pillars"][0]["id"] == "agent_benchmarks"

    # 2. Fetch active niche
    get_res = await client.get("/api/v1/niche")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["id"] == "primary"
    assert fetched["name"] == "AI Engineering & Coding Automation"

    # 3. Update niche again (must overwrite singleton "primary", never create second record)
    updated_payload = dict(SAMPLE_NICHE_PAYLOAD)
    updated_payload["name"] = "Updated AI Engineering Niche"
    put_res = await client.put("/api/v1/niche", json=updated_payload)
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["id"] == "primary"
    assert updated_data["name"] == "Updated AI Engineering Niche"

    # Verify single record remains
    verify_res = await client.get("/api/v1/niche")
    assert verify_res.status_code == 200
    assert verify_res.json()["name"] == "Updated AI Engineering Niche"
