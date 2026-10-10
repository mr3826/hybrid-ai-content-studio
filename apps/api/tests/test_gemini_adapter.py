import json

import httpx
import pytest

from app.engines.ai.adapters import gemini as gemini_module
from app.engines.ai.adapters.gemini import GeminiAdapter
from app.engines.ai.contracts import StructuredGenerationRequest, TextGenerationRequest


class _Response:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class _Client:
    def __init__(self, *, response=None, post_error=None, calls=None, **_kwargs):
        self.response = response
        self.post_error = post_error
        self.calls = calls if calls is not None else []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, *, headers, json):
        self.calls.append({"url": url, "headers": headers, "json": json})
        if self.post_error:
            raise self.post_error
        return self.response


@pytest.mark.asyncio
async def test_gemini_38_structured_request_uses_current_json_schema_format_and_tracks_usage(monkeypatch):
    calls = []
    output = {"title": "Grounded script", "sections": []}
    response = _Response(
        data={
            "candidates": [
                {
                    "content": {"parts": [{"text": json.dumps(output)}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 120,
                "candidatesTokenCount": 30,
                "thoughtsTokenCount": 5,
                "totalTokenCount": 155,
            },
        }
    )
    monkeypatch.setattr(
        gemini_module.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(response=response, calls=calls, **kwargs),
    )
    adapter = GeminiAdapter(api_key="test-gemini-key")
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Script title"},
            "sections": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {"narration": {"type": "string"}},
                    "required": ["narration"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "sections"],
        "additionalProperties": False,
    }

    result = await adapter.generate_structured(
        StructuredGenerationRequest(
            prompt="Write from evidence",
            response_schema=schema,
            max_tokens=2048,
        )
    )

    assert result.success is True
    assert result.structured_data == output
    assert result.provider == "gemini"
    assert result.model == "gemini-3.8-flash"
    assert result.prompt_tokens == 120
    assert result.completion_tokens == 35
    assert result.total_tokens == 155
    assert result.cost > 0
    assert calls[0]["url"].endswith("/models/gemini-3.8-flash:generateContent")
    assert calls[0]["headers"]["x-goog-api-key"] == "test-gemini-key"
    generation = calls[0]["json"]["generationConfig"]
    assert generation["maxOutputTokens"] == 2048
    assert generation["thinkingConfig"] == {"thinkingLevel": "low"}
    assert generation["responseFormat"]["text"]["mimeType"] == "APPLICATION_JSON"
    schema = generation["responseFormat"]["text"]["schema"]
    assert schema["type"] == "object"
    assert "responseSchema" not in generation
    assert "responseMimeType" not in generation
    assert schema["additionalProperties"] is False
    sections = schema["properties"]["sections"]
    assert sections["minItems"] == 5
    assert sections["maxItems"] == 5
    assert sections["items"]["additionalProperties"] is False
    assert sections["items"]["properties"]["narration"]["type"] == "string"
    assert "temperature" not in generation


@pytest.mark.asyncio
async def test_gemini_25_text_request_omits_gemini3_thinking_config(monkeypatch):
    calls = []
    monkeypatch.setattr(
        gemini_module.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(
            response=_Response(
                data={
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "Response"}]},
                            "finishReason": "STOP",
                        }
                    ]
                }
            ),
            calls=calls,
            **kwargs,
        ),
    )

    result = await GeminiAdapter(api_key="test-key", model="gemini-2.5-flash").generate_text(
        TextGenerationRequest(prompt="Test request")
    )

    assert result.success is True
    assert "thinkingConfig" not in calls[0]["json"]["generationConfig"]


def test_gemini_response_schema_filters_unsupported_pydantic_keywords():
    schema = GeminiAdapter._gemini_response_schema(
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "default": "unused",
                    "title": "Name",
                },
                "nested": {"type": "object", "additionalProperties": False},
            },
            "required": ["name"],
            "additionalProperties": False,
        }
    )

    assert schema == {
        "type": "object",
        "properties": {
            "name": {"type": "string", "title": "Name"},
            "nested": {"type": "object", "additionalProperties": False},
        },
        "required": ["name"],
        "additionalProperties": False,
    }


@pytest.mark.asyncio
async def test_gemini_structured_http_error_preserves_provider_diagnostic_and_redacts_key(monkeypatch):
    provider_message = (
        "Invalid value at 'generation_config.response_format.text.schema.properties.output.type' "
        "(type.googleapis.com/google.ai.generativelanguage.v1beta.Schema.Type)"
    )
    monkeypatch.setattr(
        gemini_module.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(
            response=_Response(
                status_code=400,
                text=json.dumps(
                    {
                        "error": {
                            "code": 400,
                            "status": "INVALID_ARGUMENT",
                            "message": f"{provider_message} test-gemini-key",
                        }
                    }
                ),
            ),
            **kwargs,
        ),
    )

    result = await GeminiAdapter(api_key="test-gemini-key").generate_structured(
        StructuredGenerationRequest(
            prompt="Return an object",
            response_schema={"type": "object", "properties": {}, "required": []},
        )
    )

    assert result.success is False
    assert result.failure_category == "invalid_request"
    assert provider_message in (result.error_message or "")
    assert "INVALID_ARGUMENT" in (result.error_message or "")
    assert "test-gemini-key" not in (result.error_message or "")


@pytest.mark.asyncio
async def test_gemini_malformed_structured_output_is_classified_and_keeps_usage(monkeypatch):
    monkeypatch.setattr(
        gemini_module.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(
            response=_Response(
                data={
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "{broken"}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 80,
                        "candidatesTokenCount": 12,
                        "totalTokenCount": 92,
                    },
                }
            ),
            **kwargs,
        ),
    )
    result = await GeminiAdapter(api_key="test-key").generate_structured(
        StructuredGenerationRequest(
            prompt="Return an object",
            response_schema={"type": "object", "properties": {}, "required": []},
        )
    )

    assert result.success is False
    assert result.failure_category == "malformed_output"
    assert result.prompt_tokens == 80
    assert result.completion_tokens == 12
    assert result.cost > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "category"),
    [
        (408, "timeout"),
        (429, "rate_limit"),
        (500, "server_error"),
        (502, "server_error"),
        (503, "server_error"),
        (504, "server_error"),
        (401, "authentication"),
        (403, "authorization"),
        (400, "invalid_request"),
    ],
)
async def test_gemini_http_failures_have_typed_categories(monkeypatch, status_code, category):
    monkeypatch.setattr(
        gemini_module.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(
            response=_Response(status_code=status_code, text="provider error"), **kwargs
        ),
    )
    result = await GeminiAdapter(api_key="test-key").generate_text(
        TextGenerationRequest(prompt="Test request")
    )

    assert result.success is False
    assert result.failure_category == category


@pytest.mark.asyncio
async def test_gemini_connection_failure_is_classified_without_exposing_transport_details(
    monkeypatch,
):
    monkeypatch.setattr(
        gemini_module.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(post_error=httpx.ConnectError("private transport detail"), **kwargs),
    )
    result = await GeminiAdapter(api_key="credential-never-returned").generate_text(
        TextGenerationRequest(prompt="Test request")
    )

    assert result.success is False
    assert result.failure_category == "connection_error"
    assert "private transport detail" not in (result.error_message or "")
    assert "credential-never-returned" not in (result.error_message or "")


@pytest.mark.asyncio
async def test_gemini_safety_block_without_candidates_is_classified(monkeypatch):
    monkeypatch.setattr(
        gemini_module.httpx,
        "AsyncClient",
        lambda **kwargs: _Client(
            response=_Response(
                data={"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
            ),
            **kwargs,
        ),
    )
    result = await GeminiAdapter(api_key="test-key").generate_structured(
        StructuredGenerationRequest(
            prompt="Safety-blocked prompt",
            response_schema={"type": "object", "properties": {}, "required": []},
        )
    )

    assert result.success is False
    assert result.failure_category == "safety_refusal"
