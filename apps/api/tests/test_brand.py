import pytest
from httpx import AsyncClient

SAMPLE_BRAND_PAYLOAD = {
    "brand_name": "Practical AI Studio",
    "brand_promise": "Tested AI tools, automated workflows, and honest benchmarks without hype.",
    "audience": "Engineers, builders, and technical knowledge workers.",
    "tone": ["evidence-driven", "concise", "practical", "calm"],
    "voice_rules": [
        "Show the terminal or interface; do not merely talk about it.",
        "State costs, latency, and failure rates explicitly.",
    ],
    "preferred_vocabulary": ["benchmark", "latency", "trade-off", "failure rate"],
    "avoid_vocabulary": ["game-changer", "insane", "mind-blowing"],
    "banned_cliches": ["In today's fast-paced world...", "Let's dive right in!"],
    "claim_rules": ["Every claim must cite a benchmark run or primary source."],
    "cta_style": "Direct and educational.",
    "humor_policy": "Subtle, dry, developer-oriented.",
    "controversy_policy": "Focus on technical metrics.",
    "sponsor_policy": "Full upfront disclosure.",
    "affiliate_disclosure_style": "Clear note in description.",
    "visual_identity": {
        "primary_font": "Inter",
        "secondary_font": "JetBrains Mono",
        "caption_style": "clean-mono-highlight",
    },
    "platform_adaptations": {
        "youtube": {"default_tags": ["ai", "coding"]},
        "tiktok": {"caption_limit": 150},
    },
}


@pytest.mark.asyncio
async def test_brand_lifecycle_and_exemplars(client: AsyncClient):
    # 1. Update/Create active brand
    res = await client.put("/api/v1/brand", json=SAMPLE_BRAND_PAYLOAD)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "primary"
    assert data["brand_name"] == "Practical AI Studio"
    assert "evidence-driven" in data["tone"]

    # 2. Fetch active brand
    get_res = await client.get("/api/v1/brand")
    assert get_res.status_code == 200
    assert get_res.json()["brand_name"] == "Practical AI Studio"

    # 3. Add brand exemplar
    exemplar_payload = {
        "category": "approved_hook",
        "title": "Benchmark Hook Example",
        "content": "We tested 3 coding agents on 50 broken repos. Here is what failed first.",
        "context_note": "Proven high-retention hook style.",
        "platform": "youtube",
    }
    ex_res = await client.post("/api/v1/brand/exemplars", json=exemplar_payload)
    assert ex_res.status_code == 201
    ex_data = ex_res.json()
    assert ex_data["title"] == "Benchmark Hook Example"
    assert "id" in ex_data
    exemplar_id = ex_data["id"]

    # 4. List exemplars (with filter)
    list_res = await client.get("/api/v1/brand/exemplars?category=approved_hook")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(item["id"] == exemplar_id for item in items)

    # 5. Delete exemplar
    del_res = await client.delete(f"/api/v1/brand/exemplars/{exemplar_id}")
    assert del_res.status_code == 204

    # Verify deleted
    verify_list = await client.get("/api/v1/brand/exemplars")
    assert not any(item["id"] == exemplar_id for item in verify_list.json())
