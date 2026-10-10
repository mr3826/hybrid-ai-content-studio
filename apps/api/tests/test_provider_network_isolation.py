"""Regression checks for the process-wide offline pytest defaults."""

import httpx
import pytest
from app.core.config import settings
import phase23_test_isolation as isolation


def test_default_provider_settings_are_isolated_before_app_imports():
    assert httpx.AsyncClient.send is isolation._guarded_async_send
    assert httpx.Client.send is isolation._guarded_sync_send
    assert settings.AI_MOCK_MODE is True
    assert settings.TTS_MOCK_MODE is True
    assert settings.DATABASE_URL.endswith(":memory:")
    assert settings.GEMINI_API_KEY == "pytest-disabled-provider-credential"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://generativelanguage.googleapis.com/v1beta/models",
        "https://api.openai.com/v1/models",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
    ],
)
async def test_real_provider_transports_are_blocked_by_default(url):
    class LocalOnlyTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"Network guard allowed {request.url.host} to reach a transport")

    async with httpx.AsyncClient(transport=LocalOnlyTransport()) as client:
        with pytest.raises(RuntimeError, match="Blocked an unexpected outbound AI-provider"):
            await client.get(url)


@pytest.mark.asyncio
async def test_mock_provider_transport_remains_available():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openai.com"
        return httpx.Response(200, json={"mocked": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await client.get("https://api.openai.com/v1/models")

    assert response.status_code == 200
    assert response.json() == {"mocked": True}
