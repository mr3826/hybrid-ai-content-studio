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
    monkeypatch: Any,
    response: FakeResponse,
    calls: list[dict[str, Any]],
    *,
    post_error: Exception | None = None,
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
            if post_error is not None:
                raise post_error
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
            "usage": {
                "input_tokens": 20,
                "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                "output_tokens": 8,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 28,
            },
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
    assert calls[0]["json"]["reasoning"] == {"effort": "medium"}
    assert "temperature" not in calls[0]["json"]


@pytest.mark.asyncio
async def test_openai_structured_generation_uses_strict_schema_and_parses_object(
    monkeypatch,
):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        completed_response('{"title":"SQLite WAL","summary":"Local transactions"}'),
        calls,
    )
    adapter = OpenAIAdapter(api_key="test-key")
    request = openai_module.StructuredGenerationRequest(
        prompt="Create a short title.",
        response_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "default": ""},
                "summary": {"type": "string", "default": ""},
            },
            "required": ["title"],
        },
        max_tokens=128,
    )

    response = await adapter.generate_structured(request)

    assert response.success is True
    assert response.structured_data == {
        "title": "SQLite WAL",
        "summary": "Local transactions",
    }
    assert AIProviderEngine()._validate_structured_response(request, response).success
    text_format = calls[0]["json"]["text"]["format"]
    assert text_format["type"] == "json_schema"
    assert text_format["strict"] is True
    assert text_format["schema"]["required"] == ["title", "summary"]
    assert text_format["schema"]["additionalProperties"] is False
    assert "default" not in text_format["schema"]["properties"]["summary"]
    assert "SQLite WAL" not in calls[0]["json"]["input"]


@pytest.mark.asyncio
async def test_openai_none_reasoning_effort_keeps_requested_temperature(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(monkeypatch, completed_response("Temperature kept."), calls)
    adapter = OpenAIAdapter(api_key="test-key", reasoning_effort="none")

    response = await adapter.generate_text(
        TextGenerationRequest(prompt="Keep temperature.", temperature=0.35)
    )

    assert response.success is True
    assert calls[0]["json"]["reasoning"] == {"effort": "none"}
    assert calls[0]["json"]["temperature"] == 0.35


@pytest.mark.asyncio
async def test_openai_rejects_invalid_strict_schema_root_without_http_call(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(monkeypatch, completed_response("{}"), calls)
    request = openai_module.StructuredGenerationRequest(
        prompt="Return a list.",
        response_schema={"type": "array", "items": {"type": "string"}},
    )

    response = await OpenAIAdapter(api_key="test-key").generate_structured(request)

    assert response.success is False
    assert "object JSON Schema root" in (response.error_message or "")
    assert calls == []


@pytest.mark.asyncio
async def test_openai_refusal_is_failure_and_retains_billable_usage(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "status": "completed",
                "model": "gpt-6-luna-2026-05-18",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "Refused."}],
                    }
                ],
                "usage": {
                    "input_tokens": 20,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "output_tokens": 4,
                    "output_tokens_details": {"reasoning_tokens": 1},
                    "total_tokens": 24,
                },
            }
        ),
        calls,
    )

    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="A request that is refused.")
    )

    assert response.success is False
    assert response.model == "gpt-6-luna-2026-05-18"
    assert "refused" in (response.error_message or "").lower()
    assert response.prompt_tokens == 20
    assert response.completion_tokens == 4
    assert response.total_tokens == 24
    assert response.cost == 0.000004


@pytest.mark.asyncio
async def test_openai_incomplete_response_is_failure_and_records_usage(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output_text": "partial answer",
                "usage": {
                    "input_tokens": 40,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "output_tokens": 12,
                    "output_tokens_details": {"reasoning_tokens": 4},
                    "total_tokens": 52,
                },
            }
        ),
        calls,
    )
    adapter = OpenAIAdapter(api_key="test-key")

    response = await adapter.generate_text(TextGenerationRequest(prompt="Continue."))

    assert response.success is False
    assert response.text == ""
    assert "max output tokens" in (response.error_message or "")
    assert response.prompt_tokens == 40
    assert response.completion_tokens == 12
    assert response.total_tokens == 52
    assert response.cost == 0.00001
    assert AIProviderEngine()._is_technical_or_schema_failure(response.error_message)


@pytest.mark.asyncio
async def test_openai_content_filter_incomplete_does_not_trigger_technical_fallback(
    monkeypatch,
):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "status": "incomplete",
                "incomplete_details": {"reason": "content_filter"},
                "usage": {
                    "input_tokens": 5,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "output_tokens": 2,
                    "output_tokens_details": {"reasoning_tokens": 0},
                    "total_tokens": 7,
                },
            }
        ),
        calls,
    )
    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Filtered request.")
    )

    assert response.success is False
    assert "content filtering" in (response.error_message or "")
    assert not AIProviderEngine()._is_technical_or_schema_failure(
        response.error_message
    )


@pytest.mark.asyncio
async def test_openai_failed_server_response_is_technical_fallback_candidate(
    monkeypatch,
):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "status": "failed",
                "error": {"code": "server_error", "message": "Try again."},
                "usage": {
                    "input_tokens": 10,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "output_tokens": 0,
                    "output_tokens_details": {"reasoning_tokens": 0},
                    "total_tokens": 10,
                },
            }
        ),
        calls,
    )
    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Technical failure.")
    )

    assert response.success is False
    assert "server error" in (response.error_message or "")
    assert AIProviderEngine()._is_technical_or_schema_failure(response.error_message)
    assert response.prompt_tokens == 10
    assert response.cost == 0.000001


@pytest.mark.asyncio
async def test_openai_timeout_is_reported_without_exposing_exception_details(
    monkeypatch,
):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        completed_response("Unused."),
        calls,
        post_error=openai_module.httpx.ReadTimeout("secret-bearing transport details"),
    )

    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Timeout test.")
    )

    assert response.success is False
    assert response.error_message == "OpenAI request timed out."
    assert calls[0]["json"]["reasoning"] == {"effort": "medium"}


@pytest.mark.asyncio
async def test_openai_inconsistent_usage_fails_closed_but_records_billable_tokens(
    monkeypatch,
):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "status": "completed",
                "output_text": "Must not be accepted.",
                "usage": {
                    "input_tokens": 20,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "output_tokens": 5,
                    "output_tokens_details": {"reasoning_tokens": 1},
                    "total_tokens": 26,
                },
            }
        ),
        calls,
    )

    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Usage mismatch.")
    )

    assert response.success is False
    assert response.text == ""
    assert response.total_tokens == 26
    assert response.cost == 0.0000045
    assert "inconsistent token usage" in (response.error_message or "")


@pytest.mark.asyncio
async def test_openai_missing_cache_breakdown_fails_closed_and_budgets_worst_case(
    monkeypatch,
):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "status": "completed",
                "output_text": "Missing usage details must not pass.",
                "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
            }
        ),
        calls,
    )

    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Require cache accounting details.")
    )

    assert response.success is False
    assert response.text == ""
    assert response.cost == 0.00000225
    assert "inconsistent token usage" in (response.error_message or "")


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
    assert calls[0]["json"]["text"]["format"]["type"] == "json_schema"
    assert calls[0]["json"]["text"]["format"]["strict"] is True


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


@pytest.mark.parametrize(
    "environment_name", ["OPENAI_COTENT_STUDIO", "OPENAI_CONTENT_STUDIO"]
)
def test_settings_load_requested_and_corrected_windows_environment_names(
    monkeypatch, environment_name
):
    supplied_key = "local-test-key-do-not-display"
    for name in ("OPENAI_COTENT_STUDIO", "OPENAI_CONTENT_STUDIO", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(environment_name, supplied_key)

    loaded = Settings(_env_file=None)

    assert loaded.OPENAI_API_KEY is not None
    assert (
        hashlib.sha256(loaded.OPENAI_API_KEY.encode()).digest()
        == hashlib.sha256(supplied_key.encode()).digest()
    )


def test_openai_strict_schema_is_recursive_and_does_not_mutate_server_contract():
    schema = {
        "title": "Root",
        "type": "object",
        "properties": {
            "section": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string", "minLength": 1},
                    "visual_cue": {"type": "string", "default": ""},
                },
                "required": ["narration"],
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"kind": {"type": "string"}},
                },
            },
        },
        "required": ["section"],
    }
    original = openai_module.deepcopy(schema)

    strict = OpenAIAdapter._strict_schema(schema)

    assert schema == original
    assert strict["required"] == ["section", "sections"]
    assert strict["additionalProperties"] is False
    strict_section = strict["properties"]["section"]
    assert strict_section["required"] == ["narration", "visual_cue"]
    assert strict_section["additionalProperties"] is False
    assert "default" not in strict_section["properties"]["visual_cue"]
    item_schema = strict["properties"]["sections"]["items"]
    assert item_schema["required"] == ["kind"]
    assert item_schema["additionalProperties"] is False


@pytest.mark.asyncio
async def test_openai_missing_status_fails_closed_and_keeps_usage(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "output_text": "Untrusted success.",
                "usage": {
                    "input_tokens": 10,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                    "output_tokens": 3,
                    "output_tokens_details": {"reasoning_tokens": 1},
                    "total_tokens": 13,
                },
            }
        ),
        calls,
    )

    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="No status.")
    )

    assert response.success is False
    assert response.text == ""
    assert "completion status" in (response.error_message or "")
    assert response.total_tokens == 13
    assert response.cost == 0.0000025


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
    monkeypatch.setattr(settings, "OPENAI_REASONING_EFFORT", "high")
    engine = AIProviderEngine()

    assert engine.openai_adapter.cost_rates == {
        "prompt_per_million": 1.25,
        "cached_prompt_per_million": 0.01,
        "cache_write_prompt_per_million": 0.125,
        "completion_per_million": 6.75,
    }
    assert engine.openai_adapter.reasoning_effort == "high"


@pytest.mark.asyncio
async def test_openai_accounts_for_cached_and_cache_write_tokens(monkeypatch):
    calls: list[dict[str, Any]] = []
    install_fake_client(
        monkeypatch,
        FakeResponse(
            {
                "status": "completed",
                "output_text": "Usage details are billable.",
                "usage": {
                    "input_tokens": 1000,
                    "input_tokens_details": {
                        "cached_tokens": 400,
                        "cache_write_tokens": 200,
                    },
                    "output_tokens": 50,
                    "output_tokens_details": {"reasoning_tokens": 20},
                    "total_tokens": 1050,
                },
            }
        ),
        calls,
    )

    response = await OpenAIAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Account for real usage categories.")
    )

    assert response.success is True
    assert response.prompt_tokens == 1000
    assert response.completion_tokens == 50
    assert response.total_tokens == 1050
    assert response.cost == 0.000094


def test_openai_budget_estimate_uses_highest_cache_write_rate():
    adapter = OpenAIAdapter(api_key="test-key")

    assert adapter.calculate_cost(1000, 1000) == 0.0006
    assert adapter.calculate_max_cost(1000, 1000) == 0.000625


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


@pytest.mark.asyncio
async def test_live_openai_without_key_fails_without_mock_substitution(monkeypatch):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "AI_PRIMARY_PROVIDER", "openai")
    monkeypatch.setattr(settings, "AI_FALLBACK_ENABLED", False)
    engine = AIProviderEngine()

    response = await engine.generate_text(
        TextGenerationRequest(
            prompt="Live mode must fail closed.", preferred_provider="openai"
        )
    )

    assert response.success is False
    assert response.provider == "openai"
    assert "not configured" in (response.error_message or "")


@pytest.mark.asyncio
async def test_failed_primary_usage_is_logged_before_technical_fallback(monkeypatch):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "AI_PRIMARY_PROVIDER", "openai")
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "qwen")
    monkeypatch.setattr(settings, "AI_FALLBACK_ENABLED", True)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(settings, "QWEN_API_KEY", "test-qwen-key")
    engine = AIProviderEngine()
    logged: list[AIResponse] = []

    async def fail_primary(request):
        return AIResponse(
            text="",
            provider="openai",
            model="gpt-6-luna",
            task=request.task,
            prompt_tokens=40,
            completion_tokens=12,
            total_tokens=52,
            cost=0.00001,
            success=False,
            error_message="OpenAI response incomplete: max output tokens limit reached.",
        )

    async def satisfy_fallback(request):
        return AIResponse(
            text='{"result":"Fallback response."}',
            structured_data={"result": "Fallback response."},
            provider="qwen",
            model="qwen-plus",
            task=request.task,
            prompt_tokens=30,
            completion_tokens=10,
            total_tokens=40,
            cost=0.00002,
            success=True,
        )

    async def capture_telemetry(response, *_args, **_kwargs):
        logged.append(response.model_copy(deep=True))

    monkeypatch.setattr(engine.openai_adapter, "generate_structured", fail_primary)
    monkeypatch.setattr(engine.qwen_adapter, "generate_structured", satisfy_fallback)
    monkeypatch.setattr(engine, "_log_telemetry", capture_telemetry)
    request = openai_module.StructuredGenerationRequest(
        prompt="Use configured technical fallback.",
        response_schema={
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        },
    )

    response = await engine.generate_structured(request)

    assert response.success is True
    assert response.provider == "qwen"
    assert response.fallback_used is True
    assert [entry.provider for entry in logged] == ["openai", "qwen"]
    assert [entry.cost for entry in logged] == [0.00001, 0.00002]
    assert logged[0].completion_tokens == 12
