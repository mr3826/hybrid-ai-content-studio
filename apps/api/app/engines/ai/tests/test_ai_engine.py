import pytest
from app.engines.ai.engine import AIProviderEngine
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
)
from app.engines.core.base import EngineContext


@pytest.mark.asyncio
async def test_ai_manifest_and_rules():
    engine = AIProviderEngine()
    assert engine.id == "ai"
    assert engine.manifest.name == "AI Provider Engine"
    assert "PromptRequest" in engine.manifest.inputs
    assert "ModelResponse" in engine.manifest.outputs
    assert engine.rules.get("primary_provider") == "gemini"
    assert engine.rules.get("fallback_provider") == "qwen"
    assert engine.rules.get("fallback_enabled") is True


@pytest.mark.asyncio
async def test_ai_generate_text_mock():
    engine = AIProviderEngine()
    req = TextGenerationRequest(
        prompt="Explain why single-niche architecture eliminates context drift.",
        task="architecture_explanation",
        temperature=0.7,
    )
    resp = await engine.generate_text(req)

    assert resp.success is True
    assert resp.provider == "mock"
    assert "Studio AI Generated Response" in resp.text
    assert resp.prompt_tokens > 0
    assert resp.completion_tokens > 0
    assert resp.total_tokens == resp.prompt_tokens + resp.completion_tokens
    assert resp.fallback_used is False


@pytest.mark.asyncio
async def test_ai_generate_structured_mock():
    engine = AIProviderEngine()
    schema = {
        "type": "object",
        "properties": {
            "hook_title": {"type": "string"},
            "estimated_engagement_score": {"type": "number"},
            "is_evergreen": {"type": "boolean"},
        },
        "required": ["hook_title", "estimated_engagement_score", "is_evergreen"],
    }
    req = StructuredGenerationRequest(
        prompt="Generate an attention-grabbing hook for local LLM inference.",
        response_schema=schema,
        task="hook_generation",
    )
    resp = await engine.generate_structured(req)

    assert resp.success is True
    assert resp.structured_data is not None
    assert "hook_title" in resp.structured_data
    assert "estimated_engagement_score" in resp.structured_data
    assert resp.structured_data["is_evergreen"] is True


@pytest.mark.asyncio
async def test_ai_analyze_mock():
    engine = AIProviderEngine()
    req = AnalyzeRequest(
        content="Testing token generation latency on Apple M4 Max with 128GB unified memory.",
        instruction="Verify factual tone and brand alignment.",
        criteria=["clarity", "verifiable_metrics", "no_hyperbole"],
        task="content_audit",
    )
    resp = await engine.analyze(req)

    assert resp.success is True
    assert resp.structured_data is not None
    assert resp.structured_data.get("score") > 80.0
    assert resp.structured_data.get("passed") is True
    assert len(resp.structured_data.get("observations", [])) >= 1


@pytest.mark.asyncio
async def test_technical_fallback():
    engine = AIProviderEngine()

    # Simulate technical 503 error on primary
    req = TextGenerationRequest(
        prompt="Compare DeepSeek V3 vs Llama 3.3.",
        task="model_comparison",
        allow_fallback=True,
        simulate_failure="server_error",
    )
    resp = await engine.generate_text(req)

    # In mock mode, fallback adapter succeeds and records fallback metadata
    assert resp.success is True
    assert resp.fallback_used is True
    assert "503" in (resp.fallback_reason or "")
    assert resp.primary_provider == "mock"


@pytest.mark.asyncio
async def test_schema_error_fallback():
    engine = AIProviderEngine()

    schema = {"type": "object", "properties": {"verdict": {"type": "string"}}}
    req = StructuredGenerationRequest(
        prompt="Extract verdict",
        response_schema=schema,
        allow_fallback=True,
        simulate_failure="schema_error",
    )
    resp = await engine.generate_structured(req)

    assert resp.success is True
    assert resp.fallback_used is True
    assert "JSONDecodeError" in (resp.fallback_reason or "")


@pytest.mark.asyncio
async def test_forbidden_factual_fallback_rejection():
    engine = AIProviderEngine()

    # If the error is an editorial/factual rejection, fallback must NOT trigger
    is_tech = engine._is_technical_or_schema_failure("Insufficient_evidence provided in source packet")
    assert is_tech is False

    is_tech_claim = engine._is_technical_or_schema_failure("Unsupported_claim detected by verification policy")
    assert is_tech_claim is False

    is_real_tech = engine._is_technical_or_schema_failure("HTTP 429: Too Many Requests")
    assert is_real_tech is True


@pytest.mark.asyncio
async def test_ai_engine_run_and_explain():
    engine = AIProviderEngine()
    context = EngineContext(
        run_id="test-ai-run-1",
        dry_run=True,
        trigger="manual",
        parameters={"prompt": "Studio prompt test", "task": "benchmark"},
    )
    result = await engine.run(context)

    assert result.engine_id == "ai"
    assert result.success is True
    assert result.output_count == 1
    assert len(result.explanations) == 1

    sync_health = engine.health()
    assert sync_health.status == "healthy"

    health = await engine.health_check()
    assert health.status == "healthy"

    explanation = engine.explain("test-ai-run-1")
    assert "AI Provider Engine" in explanation.summary
    assert len(explanation.factors) >= 4
