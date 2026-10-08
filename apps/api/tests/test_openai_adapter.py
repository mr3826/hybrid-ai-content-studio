"""OpenAI provider contract tests; all HTTP traffic is intercepted locally."""

import hashlib
from typing import Any

import pytest

from app.core.config import Settings, settings
from app.engines.ai.adapters import openai as openai_module
from app.engines.ai.adapters.openai import OpenAIAdapter
from app.engines.ai.contracts import AIResponse, AnalyzeRequest, TextGenerationRequest
from app.engines.ai.engine import AIProviderEngine
from pydantic import ValidationError


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200, text: str = "") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text or str(payload)

    def json(self) -> Any:
        return self._payload


def install_fake_client(
    monkeypatch: Any, response: FakeResponse, calls: list[dict[str, Any]]
) -> None:
    class FakeAsyncClient:
        def __init__(self, **_kwargs: Any):
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def post(
            self, url: str, *, headers: dict[str, str], json: dict[str, Any]
        ):
            calls.append({"url": url, "headers": headers, "json": json})
            return response

    monkeypatch.setattr(openai_module.httpx, "AsyncClient", FakeAsyncClient)


def completed_response(text: str) -> FakeResponse:
    return FakeResponse(
        {
            "status": "completed",
            "model": "gpt-6-luna",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
            "usage": {"input_tokens": 20, "output_tokens": 8, "total_tokens": 28},
        }
    )


@pytest.mark.asyncio
async def test_openai_text_uses_responses_api_and_reports_actual_usage(monkeypatch):
    key = "test-openai-key-never-print"
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch, completed_response("A real provider response."), calls
    )
    adapter = OpenAIAdapter(api_key=key)

    response = await adapter.generate_text(
        TextGenerationRequest(prompt="Write one sentence.", system_prompt="Be concise.")
    )

    assert response.success is True
    assert response.provider == "openai"
    assert response.model == "gpt-6-luna"
    assert response.text == "A real provider response."
    assert response.prompt_tokens == 20
    assert response.completion_tokens == 8
    assert response.total_tokens == 28
    assert response.cost == 0.000006
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.openai.com/v1/responses"
    assert calls[0]["headers"]["Authorization"] == f"Bearer {key}"
    assert key not in calls[0]["url"]
    assert calls[0]["json"]["instructions"] == "Be concise."
    assert calls[0]["json"]["store"] is False


@pytest.mark.asyncio
async def test_openai_structured_generation_uses_json_mode_and_parses_object(
    monkeypatch,
):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch, completed_response('{"title":"SQLite WAL"}'), calls
    )
    adapter = OpenAIAdapter(api_key="test-key")
    request = openai_module.StructuredGenerationRequest(
        prompt="Create a short title.",
        response_schema={
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
        max_tokens=128,
    )

    response = await adapter.generate_structured(request)

    assert response.success is True
    assert response.structured_data == {"title": "SQLite WAL"}
    assert calls[0]["json"]["text"] == {"format": {"type": "json_object"}}
    assert "SQLite WAL" not in calls[0]["json"]["input"]
    assert "JSON Schema" in calls[0]["json"]["input"]


@pytest.mark.asyncio
async def test_openai_analyze_uses_machine_readable_result_contract(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        completed_response(
            '{"score":92,"passed":true,"observations":["Claim matches the supplied source."]}'
        ),
        calls,
    )

    response = await OpenAIAdapter(api_key="test-key").analyze(
        AnalyzeRequest(
            content="A source-grounded claim.",
            instruction="Review the claim.",
            criteria=["evidence"],
        )
    )

    assert response.success is True
    assert response.structured_data == {
        "score": 92,
        "passed": True,
        "observations": ["Claim matches the supplied source."],
    }
    assert "Analyze the following content" in calls[0]["json"]["input"]
    assert calls[0]["json"]["text"] == {"format": {"type": "json_object"}}


@pytest.mark.asyncio
async def test_openai_simulated_schema_failure_does_not_call_provider(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(monkeypatch, completed_response("{}"), calls)
    request = openai_module.StructuredGenerationRequest(
        prompt="Return a JSON object.",
        response_schema={"type": "object"},
        simulate_failure="schema_error",
    )

    response = await OpenAIAdapter(api_key="test-key").generate_structured(request)

    assert response.success is False
    assert "Schema parsing error" in (response.error_message or "")
    assert calls == []


@pytest.mark.asyncio
async def test_openai_missing_key_and_usage_fail_closed(monkeypatch):
    calls: list[dict[str, Any]] = []
    adapter = OpenAIAdapter()
    missing = await adapter.generate_text(
        TextGenerationRequest(prompt="No request should be sent.")
    )
    assert missing.success is False
    assert "not configured" in (missing.error_message or "")

    install_fake_client(
        monkeypatch,
        FakeResponse({"status": "completed", "output_text": "Unmetered response."}),
        calls,
    )
    unmetered = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Do not report zero cost.")
    )
    assert unmetered.success is False
    assert "token usage" in (unmetered.error_message or "")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_openai_errors_redact_key_and_preserve_http_diagnostics(monkeypatch):
    key = "test-secret-that-must-be-redacted"
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse({"error": {"message": f"Bad token {key}"}}, status_code=401),
        calls,
    )

    response = await OpenAIAdapter(api_key=key).generate_text(
        TextGenerationRequest(prompt="Test authorization error.")
    )

    assert response.success is False
    assert "HTTP 401" in (response.error_message or "")
    assert "[REDACTED]" in (response.error_message or "")
    assert key not in (response.error_message or "")


def test_settings_load_requested_windows_environment_name(monkeypatch):
    supplied_key = "local-test-key-do-not-display"
    monkeypatch.setenv("OPENAI_COTENT_STUDIO", supplied_key)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    loaded = Settings(_env_file=None)

    assert loaded.OPENAI_API_KEY is not None
    assert (
        hashlib.sha256(loaded.OPENAI_API_KEY.encode()).digest()
        == hashlib.sha256(supplied_key.encode()).digest()
    )


def test_openai_provider_is_validated_by_the_public_request_contract():
    request = TextGenerationRequest(prompt="Use OpenAI.", preferred_provider="openai")
    assert request.preferred_provider == "openai"
    with pytest.raises(ValidationError):
        TextGenerationRequest(
            prompt="Reject unknown provider.", preferred_provider="unknown"
        )


def test_openai_can_be_selected_as_primary_and_fallback(monkeypatch):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "AI_PRIMARY_PROVIDER", "openai")
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    engine = AIProviderEngine()

    assert engine._get_primary_adapter().provider_id == "openai"
    assert engine._get_primary_adapter("openai").provider_id == "openai"
    assert engine._get_fallback_adapter().provider_id == "qwen"


@pytest.mark.asyncio
async def test_status_reports_configured_openai_primary(monkeypatch):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "AI_PRIMARY_PROVIDER", "openai")
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    engine = AIProviderEngine()

    status = await engine.get_status()

    assert status.primary_provider == "openai"
    assert status.primary_model == "gpt-6-luna"
    assert status.primary_configured is True


def test_openai_rates_can_be_overridden_for_a_custom_model(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_PROMPT_COST_PER_MILLION", 1.25)
    monkeypatch.setattr(settings, "OPENAI_COMPLETION_COST_PER_MILLION", 6.75)
    engine = AIProviderEngine()

    assert engine.openai_adapter.cost_rates == {
        "prompt_per_million": 1.25,
        "completion_per_million": 6.75,
    }


@pytest.mark.asyncio
async def test_openai_primary_uses_configured_fallback_on_technical_failure(
    monkeypatch,
):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "AI_PRIMARY_PROVIDER", "openai")
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "AI_FALLBACK_ENABLED", True)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "QWEN_API_KEY", "test-key")
    engine = AIProviderEngine()

    async def fail_primary(request):
        return AIResponse(
            text="",
            provider="openai",
            model="gpt-6-luna",
            task=request.task,
            success=False,
            error_message="OpenAI HTTP 503: Service unavailable.",
        )

    async def satisfy_fallback(request):
        return AIResponse(
            text="Fallback response.",
            provider="qwen",
            model="qwen-plus",
            task=request.task,
            success=True,
        )

    monkeypatch.setattr(engine.openai_adapter, "generate_text", fail_primary)
    monkeypatch.setattr(engine.qwen_adapter, "generate_text", satisfy_fallback)
    response = await engine.generate_text(
        TextGenerationRequest(prompt="Exercise failover.")
    )

    assert response.success is True
    assert response.provider == "qwen"
    assert response.fallback_used is True
    assert response.primary_provider == "openai"
