"""OpenAI Responses API adapter for production text generation."""

import json
import time
from copy import deepcopy
from typing import Any, Dict, Literal, Optional
from urllib.parse import quote

import httpx

from app.engines.ai.adapters.base import BaseAIAdapter
from app.engines.ai.contracts import (
    AnalyzeRequest,
    AIResponse,
    StructuredGenerationRequest,
    TextGenerationRequest,
)

ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh", "max"]


class OpenAIAdapter(BaseAIAdapter):
    """Production adapter using OpenAI's direct HTTPS Responses API."""

    base_url = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-6-luna",
        cost_rates: Optional[Dict[str, float]] = None,
        timeout_seconds: float = 30.0,
        reasoning_effort: ReasoningEffort = "medium",
    ):
        if reasoning_effort not in {"none", "low", "medium", "high", "xhigh", "max"}:
            raise ValueError("Unsupported GPT-6 Luna reasoning effort.")
        rates = {
            "prompt_per_million": 0.10,
            "cached_prompt_per_million": 0.01,
            "cache_write_prompt_per_million": 0.125,
            "completion_per_million": 0.50,
        }
        rates.update(cost_rates or {})
        super().__init__(
            provider_id="openai",
            default_model=model,
            cost_rates=rates,
        )
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.reasoning_effort = reasoning_effort

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost at the ordinary uncached input and output token rates."""
        prompt_rate = self.cost_rates.get("prompt_per_million", 0.0) / 1_000_000.0
        completion_rate = (
            self.cost_rates.get("completion_per_million", 0.0) / 1_000_000.0
        )
        return round(
            prompt_tokens * prompt_rate + completion_tokens * completion_rate, 10
        )

    def calculate_max_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Conservatively budget every input token at the highest cache-write rate."""
        prompt_rate = (
            max(
                self.cost_rates.get("prompt_per_million", 0.0),
                self.cost_rates.get("cached_prompt_per_million", 0.0),
                self.cost_rates.get("cache_write_prompt_per_million", 0.0),
            )
            / 1_000_000.0
        )
        completion_rate = (
            self.cost_rates.get("completion_per_million", 0.0) / 1_000_000.0
        )
        return round(
            prompt_tokens * prompt_rate + completion_tokens * completion_rate, 10
        )

    def _calculate_usage_cost(
        self, usage: Dict[str, Any], output_tokens: int
    ) -> Optional[float]:
        """Calculate actual input cost from normal, cache-read, and cache-write counts."""
        input_tokens = usage.get("input_tokens")
        details = usage.get("input_tokens_details")
        if not isinstance(details, dict):
            return None
        if "cached_tokens" not in details or "cache_write_tokens" not in details:
            return None
        cached_tokens = details.get("cached_tokens", 0)
        cache_write_tokens = details.get("cache_write_tokens", 0)
        for count in (input_tokens, cached_tokens, cache_write_tokens):
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                return None
        if cached_tokens + cache_write_tokens > input_tokens:
            return None

        ordinary_tokens = input_tokens - cached_tokens - cache_write_tokens
        input_cost = (
            ordinary_tokens * self.cost_rates.get("prompt_per_million", 0.0)
            + cached_tokens * self.cost_rates.get("cached_prompt_per_million", 0.0)
            + cache_write_tokens
            * self.cost_rates.get("cache_write_prompt_per_million", 0.0)
        ) / 1_000_000.0
        output_cost = (
            output_tokens * self.cost_rates.get("completion_per_million", 0.0)
        ) / 1_000_000.0
        return round(input_cost + output_cost, 10)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _sanitize_error(self, message: str) -> str:
        return message.replace(self.api_key, "[REDACTED]") if self.api_key else message

    def _failure(
        self,
        task: str,
        prompt_version: str,
        message: str,
        started_at: float,
        *,
        model: Optional[str] = None,
        usage: Any = None,
    ) -> AIResponse:
        response = AIResponse(
            text="",
            structured_data=None,
            provider=self.provider_id,
            model=model or self.default_model,
            task=task,
            prompt_version=prompt_version,
            success=False,
            error_message=self._sanitize_error(message),
            latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )
        self._apply_usage(response, usage)
        return response

    def _apply_usage(self, response: AIResponse, usage: Any) -> bool:
        """Record billable input/output tokens, even for failed provider responses."""
        if not isinstance(usage, dict):
            return False
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        if (
            not isinstance(input_tokens, int)
            or isinstance(input_tokens, bool)
            or input_tokens < 0
            or not isinstance(output_tokens, int)
            or isinstance(output_tokens, bool)
            or output_tokens < 0
        ):
            return False

        response.prompt_tokens = input_tokens
        response.completion_tokens = output_tokens
        # OpenAI output_tokens includes reasoning tokens and remains billable even if
        # the response is incomplete or refused.
        actual_cost = self._calculate_usage_cost(usage, output_tokens)
        response.cost = (
            actual_cost
            if actual_cost is not None
            else self.calculate_max_cost(input_tokens, output_tokens)
        )
        if (
            not isinstance(total_tokens, int)
            or isinstance(total_tokens, bool)
            or total_tokens < 0
        ):
            response.total_tokens = input_tokens + output_tokens
            return False
        response.total_tokens = total_tokens
        return total_tokens == input_tokens + output_tokens and actual_cost is not None

    @staticmethod
    def _strict_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Project a server schema into OpenAI strict Structured Outputs form.

        Required fields and additional-property checks remain enforced again by the
        AI engine against the original request schema after parsing.
        """

        def normalize(value: Any) -> Any:
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if not isinstance(value, dict):
                return value

            normalized: Dict[str, Any] = {}
            for key, item in value.items():
                if key in {"title", "default"}:
                    continue
                if key == "properties" and isinstance(item, dict):
                    # Property names are user schema keys; a field named "title"
                    # must not be confused with the JSON Schema title annotation.
                    normalized[key] = {
                        property_name: normalize(property_schema)
                        for property_name, property_schema in item.items()
                    }
                elif key in {"$defs", "definitions"} and isinstance(item, dict):
                    normalized[key] = {
                        definition_name: normalize(definition_schema)
                        for definition_name, definition_schema in item.items()
                    }
                else:
                    normalized[key] = normalize(item)
            properties = normalized.get("properties")
            if isinstance(properties, dict):
                normalized["type"] = "object"
                normalized["required"] = list(properties)
                normalized["additionalProperties"] = False
            elif normalized.get("type") == "object":
                normalized["properties"] = {}
                normalized["required"] = []
                normalized["additionalProperties"] = False
            return normalized

        strict_schema = normalize(deepcopy(schema))
        if not isinstance(strict_schema, dict) or strict_schema.get("type") != "object":
            raise ValueError(
                "OpenAI Structured Outputs requires an object JSON Schema root."
            )
        return strict_schema

    @staticmethod
    def _contains_refusal(data: Dict[str, Any]) -> bool:
        refusal = data.get("refusal")
        if isinstance(refusal, str) and refusal.strip():
            return True
        output = data.get("output")
        if not isinstance(output, list):
            return False
        for item in output:
            if not isinstance(item, dict):
                continue
            content_items = item.get("content")
            if not isinstance(content_items, list):
                continue
            if any(
                isinstance(content, dict) and content.get("type") == "refusal"
                for content in content_items
            ):
                return True
        return False

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        chunks: list[str] = []
        output = data.get("output", [])
        if not isinstance(output, list):
            return ""
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content_items = item.get("content", [])
            if not isinstance(content_items, list):
                continue
            for content in content_items:
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
        return "".join(chunks).strip()

    async def _generate(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str],
        task: str,
        prompt_version: str,
        temperature: float,
        max_tokens: int,
        structured_schema: Optional[Dict[str, Any]] = None,
        simulate_failure: Optional[str] = None,
    ) -> AIResponse:
        started_at = time.perf_counter()
        if max_tokens < 16:
            return self._failure(
                task,
                prompt_version,
                "OpenAI Responses API requires max_output_tokens to be at least 16.",
                started_at,
            )

        if simulate_failure == "rate_limit":
            return self._failure(
                task,
                prompt_version,
                "OpenAI HTTP 429: Rate limit exceeded.",
                started_at,
            )
        if simulate_failure in ("server_error", "timeout"):
            return self._failure(
                task,
                prompt_version,
                "OpenAI HTTP 503: Simulated service unavailable.",
                started_at,
            )
        if simulate_failure == "schema_error":
            return self._failure(
                task,
                prompt_version,
                "Schema parsing error: Simulated malformed JSON output.",
                started_at,
            )
        if not self.api_key:
            return self._failure(
                task,
                prompt_version,
                "OpenAI API key is not configured (set OPENAI_COTENT_STUDIO or OPENAI_API_KEY).",
                started_at,
            )

        payload: Dict[str, Any] = {
            "model": self.default_model,
            "input": prompt,
            "max_output_tokens": max_tokens,
            "reasoning": {"effort": self.reasoning_effort},
            # Script and research prompts can contain private local workspace data.
            "store": False,
        }
        # GPT-6 rejects sampling parameters when reasoning effort is active.
        if self.reasoning_effort == "none":
            payload["temperature"] = temperature
        if system_prompt:
            payload["instructions"] = system_prompt
        if structured_schema is not None:
            try:
                strict_schema = self._strict_schema(structured_schema)
            except ValueError as exc:
                return self._failure(
                    task,
                    prompt_version,
                    str(exc),
                    started_at,
                )
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "studio_structured_output",
                    "strict": True,
                    "schema": strict_schema,
                }
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/responses",
                    headers=self._get_headers(),
                    json=payload,
                )

            if response.status_code < 200 or response.status_code >= 300:
                detail = response.text[:200]
                try:
                    response_data = response.json()
                    error_data = (
                        response_data.get("error", {})
                        if isinstance(response_data, dict)
                        else {}
                    )
                    if isinstance(error_data, dict) and isinstance(
                        error_data.get("message"), str
                    ):
                        detail = error_data["message"][:200]
                except (ValueError, TypeError):
                    pass
                return self._failure(
                    task,
                    prompt_version,
                    f"OpenAI HTTP {response.status_code}: {detail}",
                    started_at,
                )

            data = response.json()
            if not isinstance(data, dict):
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI returned an invalid response object.",
                    started_at,
                )
            response_model = data.get("model")
            response_model = (
                response_model
                if isinstance(response_model, str) and response_model
                else self.default_model
            )
            usage = data.get("usage")
            response_status = data.get("status")
            if not isinstance(response_status, str) or not response_status:
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI response is missing a valid completion status.",
                    started_at,
                    model=response_model,
                    usage=usage,
                )
            if response_status != "completed":
                incomplete_details = data.get("incomplete_details")
                reason = (
                    incomplete_details.get("reason")
                    if isinstance(incomplete_details, dict)
                    else None
                )
                if response_status == "incomplete" and reason == "max_output_tokens":
                    detail = (
                        "OpenAI response incomplete: max output tokens limit reached."
                    )
                elif response_status == "incomplete" and reason == "content_filter":
                    detail = "OpenAI response incomplete due to content filtering."
                elif response_status == "failed":
                    error = data.get("error")
                    code = error.get("code") if isinstance(error, dict) else None
                    provider_message = (
                        error.get("message") if isinstance(error, dict) else None
                    )
                    if isinstance(code, str) and code:
                        detail = f"OpenAI response failed ({code.replace('_', ' ')})"
                    else:
                        detail = "OpenAI response failed without a provider error code"
                    if isinstance(provider_message, str) and provider_message:
                        detail += f": {provider_message[:200]}"
                    else:
                        detail += "."
                else:
                    suffix = f" ({reason})" if isinstance(reason, str) else ""
                    detail = (
                        f"OpenAI response did not complete: {response_status}{suffix}."
                    )
                return self._failure(
                    task,
                    prompt_version,
                    detail,
                    started_at,
                    model=response_model,
                    usage=usage,
                )

            if self._contains_refusal(data):
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI refused to generate this response.",
                    started_at,
                    model=response_model,
                    usage=usage,
                )

            text = self._extract_text(data)
            if not text:
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI returned no assistant text output.",
                    started_at,
                    model=response_model,
                    usage=usage,
                )

            result = AIResponse(
                text=text,
                structured_data=None,
                provider=self.provider_id,
                model=response_model,
                task=task,
                prompt_version=prompt_version,
                latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
                success=True,
            )
            if not self._apply_usage(result, usage):
                result.success = False
                result.text = ""
                result.error_message = (
                    "OpenAI returned missing or inconsistent token usage data; "
                    "refusing to report an unmeasured production result."
                )
            return result
        except httpx.TimeoutException:
            return self._failure(
                task, prompt_version, "OpenAI request timed out.", started_at
            )
        except httpx.HTTPError as exc:
            return self._failure(
                task,
                prompt_version,
                f"OpenAI transport error: {type(exc).__name__}.",
                started_at,
            )
        except (ValueError, TypeError, AttributeError) as exc:
            return self._failure(
                task,
                prompt_version,
                f"OpenAI response parsing failed ({type(exc).__name__}).",
                started_at,
            )

    async def generate_text(self, request: TextGenerationRequest) -> AIResponse:
        """Generate plain text and report provider usage from the returned response."""
        return await self._generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            task=request.task,
            prompt_version=request.prompt_version,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            simulate_failure=request.simulate_failure,
        )

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> AIResponse:
        """Generate JSON, then leave contract validation to the central AI engine."""
        response = await self._generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            task=request.task,
            prompt_version=request.prompt_version,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            structured_schema=request.response_schema,
            simulate_failure=request.simulate_failure,
        )
        if not response.success:
            return response

        try:
            parsed = json.loads(response.text)
        except json.JSONDecodeError:
            response.success = False
            response.text = ""
            response.error_message = (
                "Schema parsing error: OpenAI returned malformed JSON."
            )
            return response
        if not isinstance(parsed, dict):
            response.success = False
            response.text = ""
            response.error_message = (
                "Schema parsing error: OpenAI did not return a JSON object."
            )
            return response
        response.structured_data = parsed
        return response

    async def analyze(self, request: AnalyzeRequest) -> AIResponse:
        """Return a machine-readable analysis using the standard provider contract."""
        criteria_text = (
            ", ".join(request.criteria) if request.criteria else "general quality"
        )
        analysis_request = StructuredGenerationRequest(
            prompt=(
                f"Analyze the following content for {criteria_text}.\n"
                f"Instructions: {request.instruction}\n\nContent:\n{request.content}"
            ),
            response_schema={
                "type": "object",
                "properties": {
                    "score": {"type": "number", "minimum": 0, "maximum": 100},
                    "passed": {"type": "boolean"},
                    "observations": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["score", "passed", "observations"],
                "additionalProperties": False,
            },
            system_prompt="Analyze only the supplied content and return the requested JSON object.",
            task=request.task,
            prompt_version=request.prompt_version,
            temperature=request.temperature,
            preferred_provider=request.preferred_provider,
            allow_fallback=request.allow_fallback,
            max_tokens=2048,
            simulate_failure=request.simulate_failure,
            metadata=request.metadata,
        )
        return await self.generate_structured(analysis_request)

    async def health_check(self) -> Dict[str, Any]:
        """Check key validity and configured model access without exposing credentials."""
        if not self.api_key:
            return {
                "status": "unconfigured",
                "message": "OpenAI API key is not configured.",
            }
        model_path = quote(self.default_model, safe="-._")
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.base_url}/models/{model_path}",
                    headers=self._get_headers(),
                )
            if response.status_code == 200:
                return {"status": "healthy", "model": self.default_model}
            return {
                "status": "unhealthy",
                "message": self._sanitize_error(
                    f"OpenAI HTTP {response.status_code}: {response.text[:200]}"
                ),
            }
        except httpx.TimeoutException:
            return {"status": "unhealthy", "message": "OpenAI health check timed out."}
        except httpx.HTTPError as exc:
            return {
                "status": "unhealthy",
                "message": f"OpenAI transport error: {type(exc).__name__}.",
            }
