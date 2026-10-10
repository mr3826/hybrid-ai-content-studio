import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.engines.ai.engine import AIProviderEngine
from app.api.v1.ai import get_ai_engine
from app.main import app


@pytest.mark.asyncio
async def test_ai_api_status(client: AsyncClient, monkeypatch):
    res = await client.get("/api/v1/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "mock_mode" in data
    assert data["primary_provider"] == "gemini"
    assert data["fallback_provider"] == "none"
    assert data["fallback_enabled"] is False
    assert data["daily_budget_limit"] > 0.0


@pytest.mark.asyncio
async def test_ai_status_exposes_gemini_readiness_without_secrets(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", True)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "status-gemini-secret")
    engine = AIProviderEngine()
    monkeypatch.setitem(app.dependency_overrides, get_ai_engine, lambda: engine)

    response = await client.get("/api/v1/ai/status")

    assert response.status_code == 200
    data = response.json()
    assert data["mock_mode"] is True
    assert data["primary_provider"] == "gemini"
    assert data["primary_configured"] is True
    assert data["fallback_provider"] == "none"
    assert data["fallback_configured"] is False
    assert data["fallback_model"] == ""
    assert data["fallback_enabled"] is False
    assert "status-gemini-secret" not in response.text


@pytest.mark.asyncio
async def test_ai_api_generate_text_and_logging(client: AsyncClient):
    req_body = {
        "prompt": "Explain why empirical benchmarks build higher audience retention.",
        "task": "retention_benchmarks",
        "temperature": 0.5,
    }
    res = await client.post("/api/v1/ai/generate-text", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["text"] != ""
    assert data["total_tokens"] > 0
    assert data["fallback_used"] is False

    # Check that invocation was logged
    logs_res = await client.get("/api/v1/ai/logs?limit=5")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1

    matching = next((l for l in logs if l["task"] == "retention_benchmarks"), None)
    assert matching is not None
    assert matching["total_tokens"] > 0
    assert "api_key" not in matching  # Zero secrets invariant!


@pytest.mark.asyncio
async def test_ai_api_generate_structured(client: AsyncClient):
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "metrics": {"type": "array", "items": {"type": "string"}},
            "target_duration_seconds": {"type": "integer"},
        },
        "required": ["title", "metrics", "target_duration_seconds"],
    }
    req_body = {
        "prompt": "Generate video outline parameters for Mac Mini M4 benchmark.",
        "response_schema": schema,
        "task": "video_outline",
    }
    res = await client.post("/api/v1/ai/generate-structured", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["structured_data"] is not None
    assert "title" in data["structured_data"]
    assert "metrics" in data["structured_data"]


@pytest.mark.asyncio
async def test_ai_api_analyze(client: AsyncClient):
    req_body = {
        "content": "DeepSeek R1 matches OpenAI o1 performance in mathematical benchmarks at 1/10th the inference cost.",
        "instruction": "Audit cost claims and empirical support.",
        "criteria": ["cost_accuracy", "claim_verifiability"],
        "task": "claim_audit",
    }
    res = await client.post("/api/v1/ai/analyze", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["structured_data"] is not None
    assert data["structured_data"]["passed"] is True


@pytest.mark.asyncio
async def test_ai_api_failure_does_not_route_to_fallback(client: AsyncClient):
    req_body = {
        "prompt": "Simulated hardware benchmark test with server overload",
        "task": "fallback_test",
        "simulate_failure": "server_error",
        "allow_fallback": True,
    }
    res = await client.post("/api/v1/ai/generate-text", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["provider"] == "mock"
    assert data["fallback_used"] is False
    assert data["failure_category"] == "server_error"
    assert [attempt["provider"] for attempt in data["provider_attempts"]] == ["mock"]


@pytest.mark.asyncio
async def test_ai_api_analytics(client: AsyncClient):
    res = await client.get("/api/v1/ai/analytics?days=7")
    assert res.status_code == 200
    data = res.json()
    assert data["total_calls"] >= 1
    assert "total_cost" in data
    assert "provider_breakdown" in data
    assert isinstance(data["provider_breakdown"], list)


@pytest.mark.asyncio
async def test_ai_api_run_engine(client: AsyncClient):
    run_body = {
        "dry_run": True,
        "task": "api_run_test",
        "prompt": "Test prompt for BaseEngine runner",
    }
    res = await client.post("/api/v1/ai/run", json=run_body)
    assert res.status_code == 200
    data = res.json()
    assert data["engine_id"] == "ai"
    assert data["success"] is True
    assert data["output_count"] == 1
