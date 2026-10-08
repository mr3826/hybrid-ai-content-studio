import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.core.config import settings
from app.engines.ai.adapters.gemini import GeminiAdapter
from app.engines.ai.adapters.qwen import QwenAdapter
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
    adapter = GeminiAdapter(api_key=fake_key, model="gemini-2.0-flash")

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
        assert captured_url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

        # Key must be present securely in x-goog-api-key header
        assert captured_headers.get("x-goog-api-key") == fake_key


@pytest.mark.asyncio
async def test_gemini_adapter_error_sanitization():
    """Verify exception and error messages sanitize credentials and replace them with [REDACTED]."""
    fake_key = "AIzaSy_SENSITIVE_LEAK_TARGET_123"
    adapter = GeminiAdapter(api_key=fake_key, model="gemini-2.0-flash")

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
async def test_qwen_adapter_error_sanitization():
    """Verify Qwen adapter sanitizes credentials in error messages."""
    fake_key = "qwen-secret-token-abcdef456"
    adapter = QwenAdapter(api_key=fake_key)

    raw_err = f"Qwen unauthorized: key {fake_key} was rejected"
    sanitized = adapter._sanitize_error(raw_err)
    assert fake_key not in sanitized
    assert "[REDACTED]" in sanitized


@pytest.mark.asyncio
async def test_gemini_and_qwen_simulate_failure_isolation():
    """Verify simulate_failure is handled deterministically without network calls in all adapters."""
    gemini = GeminiAdapter(api_key="test-key")
    qwen = QwenAdapter(api_key="test-key")

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

    # Qwen simulate_failure modes
    q_rate = await qwen.generate_text(TextGenerationRequest(prompt="t", simulate_failure="rate_limit"))
    assert q_rate.success is False
    assert "429" in q_rate.error_message

    q_srv = await qwen.generate_text(TextGenerationRequest(prompt="t", simulate_failure="server_error"))
    assert q_srv.success is False
    assert "503" in q_srv.error_message


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
