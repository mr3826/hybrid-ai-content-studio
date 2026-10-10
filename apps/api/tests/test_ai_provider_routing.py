import uuid

import pytest

from app.core.config import settings
from app.engines.ai.contracts import (
    AIResponse,
    StructuredGenerationRequest,
    TextGenerationRequest,
)
from app.engines.ai.engine import AIProviderEngine


def _response(
    *,
    success: bool,
    failure_category: str | None = None,
    error_message: str | None = None,
    structured_data=None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost: float = 0,
) -> AIResponse:
    return AIResponse(
        text="valid output" if success else "",
        structured_data=structured_data,
        provider="gemini",
        model="gemini-3.8-flash",
        task="routing_test",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost=cost,
        latency_ms=5,
        success=success,
        failure_category=failure_category,
        error_message=error_message,
    )


def _configure_gemini(monkeypatch):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini-key")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_category", ["rate_limit", "timeout", "server_error", "malformed_output"])
async def test_gemini_failure_never_routes_to_a_second_provider(monkeypatch, failure_category):
    _configure_gemini(monkeypatch)
    engine = AIProviderEngine()
    calls = []

    async def fail_once(request):
        calls.append(request)
        return _response(
            success=False,
            failure_category=failure_category,
            error_message=f"simulated {failure_category}",
        )

    monkeypatch.setattr(engine.gemini_adapter, "generate_text", fail_once)
    response = await engine.generate_text(
        TextGenerationRequest(prompt="Use evidence claim-17", allow_fallback=True)
    )

    assert response.success is False
    assert response.provider == "gemini"
    assert response.fallback_used is False
    assert response.failure_category == failure_category
    assert len(calls) == 1
    assert [attempt.provider for attempt in response.provider_attempts] == ["gemini"]


@pytest.mark.asyncio
async def test_structured_output_validation_failure_does_not_retry(monkeypatch):
    _configure_gemini(monkeypatch)
    engine = AIProviderEngine()
    calls = []
    schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"],
        "additionalProperties": False,
    }

    async def invalid_output(request):
        calls.append(request)
        return _response(success=True, structured_data={"unexpected": "field"})

    monkeypatch.setattr(engine.gemini_adapter, "generate_structured", invalid_output)
    response = await engine.generate_structured(
        StructuredGenerationRequest(
            prompt="Use evidence claim-17 only",
            response_schema=schema,
            allow_fallback=True,
        )
    )

    assert response.success is False
    assert response.failure_category == "output_schema_validation"
    assert response.provider == "gemini"
    assert response.fallback_used is False
    assert len(calls) == 1
    assert [attempt.provider for attempt in response.provider_attempts] == ["gemini"]


@pytest.mark.asyncio
async def test_invalid_local_schema_is_rejected_before_provider_call(monkeypatch):
    _configure_gemini(monkeypatch)
    engine = AIProviderEngine()
    calls = []

    async def unexpected(request):
        calls.append(request)
        return _response(success=True, structured_data={})

    monkeypatch.setattr(engine.gemini_adapter, "generate_structured", unexpected)
    response = await engine.generate_structured(
        StructuredGenerationRequest(
            prompt="Bad local schema must not call providers",
            response_schema={"type": "not-a-json-schema-type"},
        )
    )

    assert response.success is False
    assert response.failure_category == "invalid_request"
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "qwen"])
async def test_legacy_provider_names_are_rejected_for_new_live_requests(monkeypatch, provider):
    _configure_gemini(monkeypatch)
    engine = AIProviderEngine()
    calls = []

    async def unexpected(request):
        calls.append(request)
        return _response(success=True)

    monkeypatch.setattr(engine.gemini_adapter, "generate_text", unexpected)
    response = await engine.generate_text(
        TextGenerationRequest(prompt="No legacy provider", preferred_provider=provider)
    )

    assert response.success is False
    assert response.failure_category == "invalid_request"
    assert "Gemini or Mock" in (response.error_message or "")
    assert calls == []


@pytest.mark.asyncio
async def test_explicit_mock_selection_stays_offline(monkeypatch):
    _configure_gemini(monkeypatch)
    engine = AIProviderEngine()
    external_calls = []

    async def unexpected(request):
        external_calls.append(request)
        return _response(success=True)

    monkeypatch.setattr(engine.gemini_adapter, "generate_text", unexpected)
    response = await engine.generate_text(
        TextGenerationRequest(prompt="Stay local", preferred_provider="mock")
    )

    assert response.success is True
    assert response.provider == "mock"
    assert external_calls == []


@pytest.mark.asyncio
async def test_cost_estimate_covers_only_one_gemini_attempt(monkeypatch):
    _configure_gemini(monkeypatch)
    engine = AIProviderEngine()
    request = StructuredGenerationRequest(
        prompt="Write a grounded script", response_schema={"type": "object"}, max_tokens=500
    )
    expected = engine._maximum_provider_cost(engine.gemini_adapter, 20, 500)
    monkeypatch.setattr(engine, "_maximum_provider_cost", lambda adapter, prompt, output: expected)

    assert engine.estimate_max_cost(request) == expected


@pytest.mark.asyncio
async def test_single_gemini_telemetry_row_records_one_attempt(monkeypatch, db_session):
    from app.repositories.ai_repository import AIRepository

    _configure_gemini(monkeypatch)
    monkeypatch.setattr(settings, "MAX_AI_COST_PER_DAY", 100.0)
    monkeypatch.setattr(settings, "MAX_GENERATION_COST_PER_PROJECT", 100.0)
    engine = AIProviderEngine()
    task = f"gemini_only_{uuid.uuid4().hex}"

    async def succeed(request):
        return _response(
            success=True,
            prompt_tokens=12,
            completion_tokens=3,
            cost=0.0004,
        ).model_copy(update={"task": request.task})

    monkeypatch.setattr(engine.gemini_adapter, "generate_text", succeed)
    response = await engine.generate_text(
        TextGenerationRequest(prompt="Persist single-provider provenance", task=task),
        session=db_session,
    )
    rows = await AIRepository(db_session).list_logs(task=task, limit=5)

    assert response.success is True
    assert response.provider == "gemini"
    assert response.fallback_used is False
    assert len(response.provider_attempts) == 1
    assert len(rows) == 1
    assert rows[0].provider == "gemini"
    assert rows[0].fallback_used is False
    assert [entry["provider"] for entry in rows[0].extra_metadata["provider_attempts"]] == ["gemini"]
