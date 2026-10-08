import json
import time
from typing import Any, Dict, Optional
import httpx
from app.engines.ai.adapters.base import BaseAIAdapter
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
    AIResponse,
)


class GeminiAdapter(BaseAIAdapter):
    """Production adapter for Google Gemini models using direct REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        cost_rates: Optional[Dict[str, float]] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(
            provider_id="gemini",
            default_model=model,
            cost_rates=cost_rates or {"prompt_per_million": 0.10, "completion_per_million": 0.40},
        )
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key
        return headers

    def _sanitize_error(self, message: str) -> str:
        if not message:
            return ""
        sanitized = message
        if self.api_key:
            sanitized = sanitized.replace(self.api_key, "[REDACTED]")
        return sanitized

    async def generate_text(self, request: TextGenerationRequest) -> AIResponse:
        start_time = time.perf_counter()

        if request.simulate_failure == "rate_limit":
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="Gemini HTTP 429: Resource exhausted (Rate limit exceeded).",
                latency_ms=round(latency_ms, 2),
            )

        if request.simulate_failure in ("server_error", "timeout"):
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="Gemini HTTP 503: The model is overloaded. Please try again later.",
                latency_ms=round(latency_ms, 2),
            )

        if not self.api_key:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="Gemini API key is not configured in settings or environment.",
                latency_ms=round(latency_ms, 2),
            )

        endpoint = f"{self.base_url}/models/{self.default_model}:generateContent"

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(endpoint, headers=self._get_headers(), json=payload)

            latency_ms = (time.perf_counter() - start_time) * 1000

            if resp.status_code != 200:
                raw_err = f"Gemini HTTP {resp.status_code}: {resp.text[:200]}"
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message=self._sanitize_error(raw_err),
                    latency_ms=round(latency_ms, 2),
                )

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message="Gemini returned no candidates in response.",
                    latency_ms=round(latency_ms, 2),
                )

            content_parts = candidates[0].get("content", {}).get("parts", [])
            text_out = "".join(part.get("text", "") for part in content_parts)

            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", max(1, len(request.prompt.split())))
            completion_tokens = usage.get("candidatesTokenCount", max(1, len(text_out.split())))
            total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            return AIResponse(
                text=text_out,
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=round(latency_ms, 2),
                success=True,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            raw_err = f"Gemini connection error: {str(e)}"
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=self._sanitize_error(raw_err),
                latency_ms=round(latency_ms, 2),
            )

    async def generate_structured(self, request: StructuredGenerationRequest) -> AIResponse:
        start_time = time.perf_counter()

        if request.simulate_failure in ("server_error", "rate_limit"):
            latency_ms = (time.perf_counter() - start_time) * 1000
            err_code = "429" if request.simulate_failure == "rate_limit" else "503"
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=f"Gemini HTTP {err_code}: Technical failure ({request.simulate_failure})",
                latency_ms=round(latency_ms, 2),
            )

        if request.simulate_failure == "schema_error":
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="```json\n{ malformed: json ",
                structured_data=None,
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="Schema parsing error: Malformed JSON output",
                latency_ms=round(latency_ms, 2),
            )

        if not self.api_key:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="Gemini API key is not configured.",
                latency_ms=round(latency_ms, 2),
            )

        endpoint = f"{self.base_url}/models/{self.default_model}:generateContent"

        schema_prompt = (
            f"{request.prompt}\n\n"
            f"You MUST return valid JSON adhering strictly to this JSON Schema:\n"
            f"{json.dumps(request.response_schema, indent=2)}\n"
            f"Output ONLY the JSON object. Do not enclose in markdown ticks if possible."
        )

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": schema_prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
                "responseMimeType": "application/json",
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(endpoint, headers=self._get_headers(), json=payload)

            latency_ms = (time.perf_counter() - start_time) * 1000

            if resp.status_code != 200:
                raw_err = f"Gemini HTTP {resp.status_code}: {resp.text[:200]}"
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message=self._sanitize_error(raw_err),
                    latency_ms=round(latency_ms, 2),
                )

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message="Gemini returned no candidates.",
                    latency_ms=round(latency_ms, 2),
                )

            raw_text = "".join(
                part.get("text", "") for part in candidates[0].get("content", {}).get("parts", [])
            )

            # Strip markdown formatting if any
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            try:
                parsed_json = json.loads(clean_text)
            except json.JSONDecodeError as jde:
                return AIResponse(
                    text=raw_text,
                    structured_data=None,
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message=f"Schema parsing error: Malformed JSON output ({str(jde)})",
                    latency_ms=round(latency_ms, 2),
                )

            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", max(1, len(schema_prompt.split())))
            completion_tokens = usage.get("candidatesTokenCount", max(1, len(raw_text.split())))
            total_tokens = usage.get("totalTokenCount", prompt_tokens + completion_tokens)
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            return AIResponse(
                text=raw_text,
                structured_data=parsed_json,
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=round(latency_ms, 2),
                success=True,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            raw_err = f"Gemini connection error: {str(e)}"
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=self._sanitize_error(raw_err),
                latency_ms=round(latency_ms, 2),
            )

    async def analyze(self, request: AnalyzeRequest) -> AIResponse:
        structured_req = StructuredGenerationRequest(
            prompt=(
                f"Analyze the following content against the specified instructions and criteria.\n\n"
                f"Content to analyze:\n{request.content}\n\n"
                f"Instructions:\n{request.instruction}\n\n"
                f"Criteria to evaluate:\n{json.dumps(request.criteria, indent=2)}"
            ),
            response_schema={
                "type": "object",
                "properties": {
                    "score": {"type": "number"},
                    "passed": {"type": "boolean"},
                    "observations": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["score", "passed", "observations", "recommendations"],
            },
            task=request.task,
            prompt_version=request.prompt_version,
            temperature=request.temperature,
            preferred_provider=self.provider_id,
            allow_fallback=request.allow_fallback,
        )
        return await self.generate_structured(structured_req)

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "status": "degraded",
                "provider": self.provider_id,
                "model": self.default_model,
                "configured": False,
                "message": "Gemini API key is not configured.",
            }
        return {
            "status": "healthy",
            "provider": self.provider_id,
            "model": self.default_model,
            "configured": True,
            "message": "Gemini API key configured.",
        }
