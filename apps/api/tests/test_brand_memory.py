import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_brand_memory_lifecycle(client: AsyncClient):
    # 1. Record a new approved hook memory
    hook_payload = {
        "memory_type": "hook",
        "content": "Here is what happens when you stress-test Claude 3.7 on a dirty repo.",
        "context_note": "Used in short #12 with 45% completion rate",
        "usage_count": 1,
    }
    create_res = await client.post("/api/v1/brand/memory", json=hook_payload)
    assert create_res.status_code == 201
    hook_data = create_res.json()
    assert hook_data["memory_type"] == "hook"
    assert hook_data["content"] == hook_payload["content"]
    assert hook_data["usage_count"] == 1
    item_id = hook_data["id"]

    # 2. Re-record same hook content -> usage count increments
    re_res = await client.post("/api/v1/brand/memory", json=hook_payload)
    assert re_res.status_code == 201
    re_data = re_res.json()
    assert re_data["id"] == item_id
    assert re_data["usage_count"] == 2

    # 3. Record a CTA memory
    cta_payload = {
        "memory_type": "cta",
        "content": "Inspect the reproduction benchmark script linked below.",
        "context_note": "Standard educational low-friction CTA",
    }
    cta_res = await client.post("/api/v1/brand/memory", json=cta_payload)
    assert cta_res.status_code == 201

    # 4. List all memory items
    all_res = await client.get("/api/v1/brand/memory")
    assert all_res.status_code == 200
    all_items = all_res.json()
    assert len(all_items) >= 2

    # 5. Filter by memory_type
    hooks_res = await client.get("/api/v1/brand/memory?memory_type=hook")
    assert hooks_res.status_code == 200
    hooks = hooks_res.json()
    assert all(h["memory_type"] == "hook" for h in hooks)

    # 6. Delete memory item
    del_res = await client.delete(f"/api/v1/brand/memory/{item_id}")
    assert del_res.status_code == 204

    # Verify deleted
    hooks_after = await client.get("/api/v1/brand/memory?memory_type=hook")
    assert not any(h["id"] == item_id for h in hooks_after.json())


@pytest.mark.asyncio
async def test_brand_monetization_metadata_fields(client: AsyncClient):
    # Fetch active brand
    get_res = await client.get("/api/v1/brand")
    assert get_res.status_code == 200
    brand = get_res.json()

    # Update with monetization fields
    brand["default_lead_magnet"] = "Local LLM Evaluation Checklist (PDF)"
    brand["newsletter_cta"] = "Join 15,000 engineers reading Practical AI Weekly."
    brand["digital_product_cta"] = "Get the Agent Production Boilerplate."

    put_res = await client.put("/api/v1/brand", json=brand)
    assert put_res.status_code == 200
    updated = put_res.json()

    assert updated["default_lead_magnet"] == "Local LLM Evaluation Checklist (PDF)"
    assert updated["newsletter_cta"] == "Join 15,000 engineers reading Practical AI Weekly."
    assert updated["digital_product_cta"] == "Get the Agent Production Boilerplate."
