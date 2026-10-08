import json
import time
from typing import Any, Dict, List, Optional
import httpx
from app.engines.ai.adapters.base import BaseAIAdapter
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
    AIResponse,
)


class QwenAdapter(BaseAIAdapter):
    """Fallback adapter for Alibaba Qwen models using OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-plus",
        cost_rates: Optional[Dict[str, float]] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(
            provider_id="qwen",
            default_model=model,
            cost_rates=cost_rates or {"prompt_per_million": 0.40, "completion_per_million": 1.20},
        )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
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
                error_message="Qwen HTTP 429: Too Many Requests (Rate limit exceeded).",
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
                error_message="Qwen HTTP 503: Service Unavailable (Model overloaded).",
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
                error_message="Qwen API key is not configured in settings or environment.",
                latency_ms=round(latency_ms, 2),
            )

        endpoint = f"{self.base_url}/chat/completions"

        messages: List[Dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload: Dict[str, Any] = {
            "model": self.default_model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(endpoint, headers=self._get_headers(), json=payload)

            latency_ms = (time.perf_counter() - start_time) * 1000

            if resp.status_code != 200:
                raw_err = f"Qwen HTTP {resp.status_code}: {resp.text[:200]}"
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
            choices = data.get("choices", [])
            if not choices:
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message="Qwen returned no choices in response.",
                    latency_ms=round(latency_ms, 2),
                )

            text_out = choices[0].get("message", {}).get("content", "")

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", max(1, len(request.prompt.split())))
            completion_tokens = usage.get("completion_tokens", max(1, len(text_out.split())))
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
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
            raw_err = f"Qwen connection error: {str(e)}"
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
                error_message=f"Qwen HTTP {err_code}: Technical failure ({request.simulate_failure})",
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
                error_message="Qwen API key is not configured.",
                latency_ms=round(latency_ms, 2),
            )

        endpoint = f"{self.base_url}/chat/completions"

        schema_prompt = (
            f"{request.prompt}\n\n"
            f"You MUST return valid JSON adhering strictly to this JSON Schema:\n"
            f"{json.dumps(request.response_schema, indent=2)}\n"
            f"Output ONLY the JSON object. Do not include markdown ticks."
        )

        messages: List[Dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": schema_prompt})

        payload: Dict[str, Any] = {
            "model": self.default_model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(endpoint, headers=self._get_headers(), json=payload)

            latency_ms = (time.perf_counter() - start_time) * 1000

            if resp.status_code != 200:
                raw_err = f"Qwen HTTP {resp.status_code}: {resp.text[:200]}"
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
            choices = data.get("choices", [])
            if not choices:
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message="Qwen returned no choices.",
                    latency_ms=round(latency_ms, 2),
                )

            raw_text = choices[0].get("message", {}).get("content", "")

            # Clean markdown JSON wrapping if any
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

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", max(1, len(schema_prompt.split())))
            completion_tokens = usage.get("completion_tokens", max(1, len(raw_text.split())))
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
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
            raw_err = f"Qwen connection error: {str(e)}"
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
            preferred_provider="qwen",
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
                "message": "Qwen API key is not configured.",
            }
        return {
            "status": "healthy",
            "provider": self.provider_id,
            "model": self.default_model,
            "configured": True,
            "message": "Qwen API key configured.",
        }
