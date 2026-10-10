"""Process-wide pytest defaults and provider egress guard."""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx
import pytest


_ENVIRONMENT_KEYS = (
    "AI_MOCK_MODE",
    "TTS_MOCK_MODE",
    "DATABASE_URL",
    "CONTENT_STUDIO_GEMINI",
    "GEMINI_API_KEY",
    "GEMINI_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_MODEL",
)
_UNSET = object()
_ORIGINAL_ENVIRONMENT: dict[str, str | object] = {
    name: os.environ.get(name, _UNSET) for name in _ENVIRONMENT_KEYS
}
_ORIGINAL_ASYNC_SEND = httpx.AsyncClient.send
_ORIGINAL_SYNC_SEND = httpx.Client.send
_LIVE_PROVIDER_TEST_RUNNING = False

_OFFLINE_ENVIRONMENT = {
    "AI_MOCK_MODE": "true",
    "TTS_MOCK_MODE": "true",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "CONTENT_STUDIO_GEMINI": "pytest-disabled-provider-credential",
    "GEMINI_API_KEY": "pytest-disabled-provider-credential",
    "GEMINI_KEY": "pytest-disabled-provider-credential",
    "GOOGLE_API_KEY": "pytest-disabled-provider-credential",
    "GEMINI_MODEL": "gemini-3.8-flash",
}
_LIVE_ENVIRONMENT = {
    "AI_MOCK_MODE": "false",
    "TTS_MOCK_MODE": "true",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
}
_LIVE_SMOKE_REQUESTED = "--run-live-provider-smoke" in sys.argv
os.environ.update(_LIVE_ENVIRONMENT if _LIVE_SMOKE_REQUESTED else _OFFLINE_ENVIRONMENT)
_AI_PROVIDER_HOSTS = {
    "generativelanguage.googleapis.com",
    "aiplatform.googleapis.com",
    "api.openai.com",
    "dashscope.aliyuncs.com",
    "dashscope-intl.aliyuncs.com",
}


def pytest_addoption(parser: Any) -> None:
    parser.addoption(
        "--run-live-provider-smoke",
        action="store_true",
        default=False,
        help="Run only the explicitly marked, one-request live Gemini smoke.",
    )


def _is_mock_transport(client: Any) -> bool:
    """Allow HTTPX mock transports while blocking real provider transports."""
    return isinstance(getattr(client, "_transport", None), httpx.MockTransport)


def _guard_provider_request(client: Any, request: httpx.Request) -> None:
    if request.url.host not in _AI_PROVIDER_HOSTS or _is_mock_transport(client):
        return
    if _LIVE_PROVIDER_TEST_RUNNING and request.url.host == "generativelanguage.googleapis.com":
        return
    raise RuntimeError(
        "Blocked an unexpected outbound AI-provider HTTP request during pytest: "
        f"{request.url.host}. Use a mocked transport or the isolated live Gemini smoke."
    )


async def _guarded_async_send(
    client: httpx.AsyncClient, request: httpx.Request, *args: Any, **kwargs: Any
) -> httpx.Response:
    _guard_provider_request(client, request)
    return await _ORIGINAL_ASYNC_SEND(client, request, *args, **kwargs)


def _guarded_sync_send(
    client: httpx.Client, request: httpx.Request, *args: Any, **kwargs: Any
) -> httpx.Response:
    _guard_provider_request(client, request)
    return _ORIGINAL_SYNC_SEND(client, request, *args, **kwargs)


def pytest_configure(config: Any) -> None:
    """Set isolated settings before application, engine, or worker modules import."""
    live_smoke = bool(config.getoption("--run-live-provider-smoke"))
    os.environ.update(_LIVE_ENVIRONMENT if live_smoke else _OFFLINE_ENVIRONMENT)
    httpx.AsyncClient.send = _guarded_async_send
    httpx.Client.send = _guarded_sync_send
    config.addinivalue_line(
        "markers",
        "live_provider: isolated Gemini smoke requiring --run-live-provider-smoke",
    )


def pytest_collection_modifyitems(config: Any, items: list[pytest.Item]) -> None:
    """Keep live provider acceptance out of ordinary or broad test runs."""
    run_live = bool(config.getoption("--run-live-provider-smoke"))
    for item in items:
        marked_live = "live_provider" in item.keywords
        if run_live and not marked_live:
            item.add_marker(pytest.mark.skip(reason="Live smoke mode runs only live_provider tests."))
        elif not run_live and marked_live:
            item.add_marker(
                pytest.mark.skip(reason="Pass --run-live-provider-smoke to opt into one live Gemini request.")
            )


def pytest_runtest_setup(item: pytest.Item) -> None:
    global _LIVE_PROVIDER_TEST_RUNNING
    _LIVE_PROVIDER_TEST_RUNNING = bool(
        item.config.getoption("--run-live-provider-smoke") and "live_provider" in item.keywords
    )


def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    del item, nextitem
    global _LIVE_PROVIDER_TEST_RUNNING
    _LIVE_PROVIDER_TEST_RUNNING = False


def pytest_unconfigure(config: Any) -> None:
    """Restore environment and HTTPX methods after each test session."""
    del config
    httpx.AsyncClient.send = _ORIGINAL_ASYNC_SEND
    httpx.Client.send = _ORIGINAL_SYNC_SEND
    for name, value in _ORIGINAL_ENVIRONMENT.items():
        if value is _UNSET:
            os.environ.pop(name, None)
        else:
            os.environ[name] = str(value)
