import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_studio_status_gates_and_export_import(client: AsyncClient):
    # 1. Check status
    status_res = await client.get("/api/v1/settings/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "niche_configured" in status_data
    assert "brand_configured" in status_data
    assert "discovery_ready" in status_data
    assert "generation_ready" in status_data

    # 2. Seed all defaults
    seed_res = await client.post("/api/v1/settings/seed-all")
    assert seed_res.status_code == 200
    seeded_status = seed_res.json()
    assert seeded_status["niche_configured"] is True
    assert seeded_status["brand_configured"] is True
    assert seeded_status["discovery_ready"] is True
    assert seeded_status["generation_ready"] is True
    assert seeded_status["is_setup_completed"] is True

    # 3. Export configuration
    export_res = await client.get("/api/v1/settings/export")
    assert export_res.status_code == 200
    config_export = export_res.json()
    assert config_export["niche"] is not None
    assert config_export["brand"] is not None
    assert "youtube" in config_export["platforms"]

    # 4. Import configuration cycle
    import_payload = {
        "niche": config_export["niche"],
        "brand": config_export["brand"],
        "platforms": config_export["platforms"],
    }
    import_res = await client.post("/api/v1/settings/import", json=import_payload)
    assert import_res.status_code == 200
    assert import_res.json()["is_setup_completed"] is True
