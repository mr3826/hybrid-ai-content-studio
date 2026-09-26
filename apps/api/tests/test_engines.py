import pytest
from httpx import AsyncClient
from app.engines.core.base import EngineManifest
from app.engines.core.catalog_engine import CatalogEngine
from app.engines.core.registry import engine_registry


@pytest.mark.asyncio
async def test_engine_catalog_listing(client: AsyncClient):
    res = await client.get("/api/v1/engines")
    assert res.status_code == 200
    engines = res.json()

    # Must contain reference engine + 13 catalog engines
    assert len(engines) >= 14
    engine_ids = [e["id"] for e in engines]
    assert "reference" in engine_ids
    assert "rss" in engine_ids
    assert "trends" in engine_ids
    assert "niche_guard" in engine_ids
    assert "opportunity" in engine_ids
    assert "brand" in engine_ids
    assert "research" in engine_ids
    assert "originality" in engine_ids
    assert "ai" in engine_ids
    assert "content" in engine_ids
    assert "media" in engine_ids
    assert "export" in engine_ids
    assert "analytics" in engine_ids
    assert "cleanup" in engine_ids

    # Verify manifest fields
    rss = next(e for e in engines if e["id"] == "rss")
    assert rss["name"] == "RSS Discovery Engine"
    assert "SourceFeed" in rss["inputs"]
    assert "DiscoveryCandidate" in rss["outputs"]
    assert "niche_guard" in rss["dependencies"]
    assert rss["health"]["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_engine_detail_and_rules(client: AsyncClient):
    res = await client.get("/api/v1/engines/reference")
    assert res.status_code == 200
    detail = res.json()
    assert detail["manifest"]["id"] == "reference"
    assert detail["health"]["status"] == "healthy"
    assert "thresholds" in detail["rules"]

    # Test update rules
    new_rules = {
        "version": "1.0.1",
        "thresholds": {"min_metric_value": 15.0},
        "weights": {"signal_strength": 0.7},
    }
    put_res = await client.put("/api/v1/engines/reference/rules", json={"rules": new_rules})
    assert put_res.status_code == 200
    assert put_res.json()["thresholds"]["min_metric_value"] == 15.0

    # Reset rules back
    reset_rules = {
        "version": "1.0.0",
        "thresholds": {"min_metric_value": 10.0},
        "weights": {"signal_strength": 0.6},
    }
    await client.put("/api/v1/engines/reference/rules", json={"rules": reset_rules})


@pytest.mark.asyncio
async def test_engine_run_and_dry_run_with_audit_logs(client: AsyncClient):
    # 1. Run engine in production mode
    run_payload = {
        "parameters": {
            "signals": [
                {"id": "sig-test-1", "title": "High Perf", "metric_value": 85.0},
                {"id": "sig-test-2", "title": "Low Perf", "metric_value": 2.0},
            ]
        }
    }
    run_res = await client.post("/api/v1/engines/reference/run", json=run_payload)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["engine_id"] == "reference"
    assert run_data["success"] is True
    assert run_data["input_count"] == 2
    assert run_data["output_count"] == 1
    assert run_data["rejected_count"] == 1

    # 2. Dry run engine
    dry_res = await client.post("/api/v1/engines/reference/dry-run", json=run_payload)
    assert dry_res.status_code == 200
    dry_data = dry_res.json()
    assert "[DRY RUN]" in dry_data["summary"]

    # 3. Check execution logs in database
    logs_res = await client.get("/api/v1/engines/reference/runs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 2
    statuses = [l["status"] for l in logs]
    assert "completed" in statuses
    assert "dry_run" in statuses

    # 4. Explainability check
    rep_id = run_data["outputs"][0]["id"]
    explain_res = await client.get(f"/api/v1/engines/reference/explain/{rep_id}")
    assert explain_res.status_code == 200
    exp = explain_res.json()
    assert exp["result_id"] == rep_id
    assert len(exp["factors"]) > 0


@pytest.mark.asyncio
async def test_engine_dependency_validation(client: AsyncClient):
    # Register a dummy engine with an unsatisfied dependency
    fake_manifest = EngineManifest(
        id="broken_engine",
        name="Broken Engine",
        version="1.0.0",
        dependencies=["non_existent_engine_xyz"],
    )
    fake_engine = CatalogEngine(manifest=fake_manifest)
    engine_registry.register(fake_engine)

    try:
        # Running should fail with HTTP 400 stating missing dependency
        res = await client.post("/api/v1/engines/broken_engine/run")
        assert res.status_code == 400
        assert "missing dependencies" in res.json()["detail"]
    finally:
        engine_registry.unregister("broken_engine")
