import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.core.config import settings
from app.engines.ai.adapters.gemini import GeminiAdapter
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
)
from app.engines.ai.engine import AIProviderEngine


@pytest.mark.asyncio
async def test_gemini_adapter_headers_and_url_without_key_in_query():
    """Verify Gemini uses x-goog-api-key header and NEVER embeds the API key in the URL query string."""
    fake_key = "AIzaSy_SECRET_CREDENTIAL_TEST_XYZ987"
    adapter = GeminiAdapter(api_key=fake_key, model="gemini-3.8-flash")

    # 1. Header check
    headers = adapter._get_headers()
    assert "x-goog-api-key" in headers
    assert headers["x-goog-api-key"] == fake_key

    # 2. Network request URL check (mocked client)
    captured_url = None
    captured_headers = None

    async def mock_post(url, headers=None, json=None, **kwargs):
        nonlocal captured_url, captured_headers
        captured_url = str(url)
        captured_headers = headers
        mock_resp = httpx.Response(
            status_code=200,
            json={
                "candidates": [{"content": {"parts": [{"text": "Synthetic test response"}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 15, "totalTokenCount": 25},
            },
            request=httpx.Request("POST", str(url)),
        )
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        req = TextGenerationRequest(prompt="Benchmark query", task="test_task")
        resp = await adapter.generate_text(req)

        assert resp.success is True
        assert captured_url is not None
        assert captured_headers is not None

        # Critical security invariant: API key must NOT be in URL
        assert fake_key not in captured_url
        assert "?key=" not in captured_url
        assert captured_url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"

        # Key must be present securely in x-goog-api-key header
        assert captured_headers.get("x-goog-api-key") == fake_key


@pytest.mark.asyncio
async def test_gemini_adapter_error_sanitization():
    """Verify exception and error messages sanitize credentials and replace them with [REDACTED]."""
    fake_key = "AIzaSy_SENSITIVE_LEAK_TARGET_123"
    adapter = GeminiAdapter(api_key=fake_key, model="gemini-3.8-flash")

    # Direct sanitizer check
    raw_leak = f"Connection failed to endpoint with credentials {fake_key} in trace"
    sanitized = adapter._sanitize_error(raw_leak)
    assert fake_key not in sanitized
    assert "[REDACTED]" in sanitized

    # Simulated connection error
    async def mock_error_post(*args, **kwargs):
        raise httpx.ConnectError(f"DNS lookup failure for {fake_key}")

    with patch("httpx.AsyncClient.post", side_effect=mock_error_post):
        req = TextGenerationRequest(prompt="Test connection error", task="test_task")
        resp = await adapter.generate_text(req)
        assert resp.success is False
        assert fake_key not in resp.error_message
        assert "[REDACTED]" in resp.error_message


@pytest.mark.asyncio
async def test_gemini_structured_generation_sends_bounded_schema_for_38():
    adapter = GeminiAdapter(api_key="test-key", model="gemini-3.8-flash")
    captured_payload = None

    async def mock_post(url, headers=None, json=None, **kwargs):
        nonlocal captured_payload
        captured_payload = json
        return httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": '{"ok":true}'}]}}
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 3,
                    "thoughtsTokenCount": 0,
                    "totalTokenCount": 13,
                },
            },
            request=httpx.Request("POST", str(url)),
        )

    schema = {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                    "additionalProperties": False,
                },
                "minItems": 1,
                "maxItems": 1,
            }
        },
        "required": ["sections"],
        "additionalProperties": False,
    }
    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        response = await adapter.generate_structured(
            StructuredGenerationRequest(prompt="Return the supplied test value.", response_schema=schema)
        )

    assert response.success is True
    assert response.structured_data == {"ok": True}
    assert captured_payload is not None
    generation_config = captured_payload["generationConfig"]
    assert generation_config["responseFormat"]["text"]["mimeType"] == "APPLICATION_JSON"
    schema = generation_config["responseFormat"]["text"]["schema"]
    assert schema["type"] == "object"
    sections = schema["properties"]["sections"]
    assert sections["items"]["type"] == "object"
    assert sections["minItems"] == 1
    assert sections["maxItems"] == 1
    assert schema["additionalProperties"] is False
    assert sections["items"]["additionalProperties"] is False
    assert "responseSchema" not in generation_config
    assert "responseMimeType" not in generation_config
    assert generation_config["thinkingConfig"] == {"thinkingLevel": "low"}
    assert "temperature" not in generation_config


@pytest.mark.asyncio
async def test_gemini_structured_generation_rejects_truncated_output():
    adapter = GeminiAdapter(api_key="test-key", model="gemini-3.8-flash")

    async def mock_post(url, headers=None, json=None, **kwargs):
        return httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"sections": ['}]}}
                ]
            },
            request=httpx.Request("POST", str(url)),
        )

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        response = await adapter.generate_structured(
            StructuredGenerationRequest(
                prompt="Return a structured response.",
                response_schema={"type": "object", "properties": {}, "required": []},
            )
        )

    assert response.success is False
    assert response.text == ""
    assert "max output tokens" in response.error_message.casefold()


@pytest.mark.asyncio
async def test_gemini_simulate_failure_isolation():
    """Verify deterministic Gemini failures do not require an outbound request."""
    gemini = GeminiAdapter(api_key="test-key")

    # Gemini simulate_failure modes
    resp_rate = await gemini.generate_text(TextGenerationRequest(prompt="t", simulate_failure="rate_limit"))
    assert resp_rate.success is False
    assert "429" in resp_rate.error_message

    resp_srv = await gemini.generate_text(TextGenerationRequest(prompt="t", simulate_failure="server_error"))
    assert resp_srv.success is False
    assert "503" in resp_srv.error_message

    resp_schema = await gemini.generate_structured(
        StructuredGenerationRequest(prompt="t", response_schema={}, simulate_failure="schema_error")
    )
    assert resp_schema.success is False
    assert "Schema parsing error" in resp_schema.error_message

@pytest.mark.asyncio
async def test_ai_provider_test_isolation_guarantee():
    """Verify default Settings and AIProviderEngine enforce mock mode during test runs."""
    assert settings.AI_MOCK_MODE is True

    engine = AIProviderEngine()
    # Primary adapter in mock mode must be MockAIAdapter
    primary = engine._get_primary_adapter()
    assert primary.provider_id == "mock"

    # Execution does not make network calls
    res = await engine.generate_text(TextGenerationRequest(prompt="Offline test prompt", task="unit_test"))
    assert res.success is True
    assert res.provider == "mock"
    assert "Studio AI Generated Response" in res.text
