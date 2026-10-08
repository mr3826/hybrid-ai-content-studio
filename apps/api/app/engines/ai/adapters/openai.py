"""OpenAI Responses API adapter for production text generation."""

import json
import time
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from app.engines.ai.adapters.base import BaseAIAdapter
from app.engines.ai.contracts import (
    AnalyzeRequest,
    AIResponse,
    StructuredGenerationRequest,
    TextGenerationRequest,
)


class OpenAIAdapter(BaseAIAdapter):
    """Production adapter using OpenAI's direct HTTPS Responses API."""

    base_url = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-6-luna",
        cost_rates: Optional[Dict[str, float]] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(
            provider_id="openai",
            default_model=model,
            cost_rates=cost_rates
            or {"prompt_per_million": 0.10, "completion_per_million": 0.50},
        )
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

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
    ) -> AIResponse:
        return AIResponse(
            text="",
            structured_data=None,
            provider=self.provider_id,
            model=self.default_model,
            task=task,
            prompt_version=prompt_version,
            success=False,
            error_message=self._sanitize_error(message),
            latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        output_text = data.get("output_text")
        if isinstance(output_text, str):
            return output_text.strip()

        chunks: list[str] = []
        for item in data.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
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
        json_mode: bool = False,
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
            "temperature": temperature,
            # Script and research prompts can contain private local workspace data.
            "store": False,
        }
        if system_prompt:
            payload["instructions"] = system_prompt
        if json_mode:
            payload["text"] = {"format": {"type": "json_object"}}

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
            response_status = data.get("status")
            if response_status and response_status != "completed":
                incomplete_details = data.get("incomplete_details")
                reason = (
                    incomplete_details.get("reason")
                    if isinstance(incomplete_details, dict)
                    else None
                )
                suffix = f" ({reason})" if isinstance(reason, str) else ""
                return self._failure(
                    task,
                    prompt_version,
                    f"OpenAI response did not complete: {response_status}{suffix}.",
                    started_at,
                )

            text = self._extract_text(data)
            if not text:
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI returned no assistant text output.",
                    started_at,
                )

            usage = data.get("usage")
            if not isinstance(usage, dict):
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI did not return token usage; refusing to report an unmeasured production cost.",
                    started_at,
                )
            prompt_tokens = usage.get("input_tokens")
            completion_tokens = usage.get("output_tokens")
            total_tokens = usage.get("total_tokens")
            if (
                not isinstance(prompt_tokens, int)
                or isinstance(prompt_tokens, bool)
                or prompt_tokens < 0
                or not isinstance(completion_tokens, int)
                or isinstance(completion_tokens, bool)
                or completion_tokens < 0
                or not isinstance(total_tokens, int)
                or isinstance(total_tokens, bool)
                or total_tokens < 0
            ):
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI returned invalid token usage data.",
                    started_at,
                )
            if total_tokens != prompt_tokens + completion_tokens:
                return self._failure(
                    task,
                    prompt_version,
                    "OpenAI returned inconsistent token usage data.",
                    started_at,
                )

            return AIResponse(
                text=text,
                structured_data=None,
                provider=self.provider_id,
                model=str(data.get("model") or self.default_model),
                task=task,
                prompt_version=prompt_version,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=self.calculate_cost(prompt_tokens, completion_tokens),
                latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
                success=True,
            )
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
        prompt = (
            f"{request.prompt}\n\n"
            "Return one JSON object, with no Markdown fences, that follows this JSON Schema:\n"
            f"{json.dumps(request.response_schema, ensure_ascii=False, indent=2)}"
        )
        response = await self._generate(
            prompt=prompt,
            system_prompt=request.system_prompt,
            task=request.task,
            prompt_version=request.prompt_version,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            json_mode=True,
            simulate_failure=request.simulate_failure,
        )
        if not response.success:
            return response

        try:
            parsed = json.loads(response.text)
        except json.JSONDecodeError:
            response.success = False
            response.error_message = (
                "Schema parsing error: OpenAI returned malformed JSON."
            )
            return response
        if not isinstance(parsed, dict):
            response.success = False
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
