import json
import time
from copy import deepcopy
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
        model: str = "gemini-3.8-flash",
        cost_rates: Optional[Dict[str, float]] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(
            provider_id="gemini",
            default_model=model,
            cost_rates=cost_rates or {"prompt_per_million": 0.75, "completion_per_million": 3.75},
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

    def _usage_metrics(
        self, data: Dict[str, Any], prompt_text: str, output_text: str
    ) -> tuple[int, int, int, float]:
        usage = data.get("usageMetadata", {})
        if not isinstance(usage, dict):
            usage = {}
        prompt_tokens = usage.get("promptTokenCount")
        completion_tokens = usage.get("candidatesTokenCount")
        thoughts_tokens = usage.get("thoughtsTokenCount", 0)
        if not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool):
            prompt_tokens = max(1, len(prompt_text.split()))
        if not isinstance(completion_tokens, int) or isinstance(completion_tokens, bool):
            completion_tokens = max(1, len(output_text.split()))
        if not isinstance(thoughts_tokens, int) or isinstance(thoughts_tokens, bool):
            thoughts_tokens = 0
        completion_tokens += thoughts_tokens
        total_tokens = usage.get("totalTokenCount")
        if not isinstance(total_tokens, int) or isinstance(total_tokens, bool):
            total_tokens = prompt_tokens + completion_tokens
        return (
            prompt_tokens,
            completion_tokens,
            total_tokens,
            self.calculate_cost(prompt_tokens, completion_tokens),
        )

    @staticmethod
    def _gemini_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert the provider-neutral JSON Schema contract to Gemini Schema enums."""
        definitions = schema.get("$defs", {}) if isinstance(schema, dict) else {}
        type_names = {
            "array": "ARRAY",
            "boolean": "BOOLEAN",
            "integer": "INTEGER",
            "null": "NULL",
            "number": "NUMBER",
            "object": "OBJECT",
            "string": "STRING",
        }
        # The GenerateContent ``responseSchema`` field uses Google's Schema
        # message, which rejects JSON Schema's ``additionalProperties`` even
        # though the engine's local validator enforces it after generation.
        supported_keys = {
            "description",
            "enum",
            "items",
            "maximum",
            "maxItems",
            "minimum",
            "minItems",
            "properties",
            "required",
            "type",
        }

        def convert(node: Any, active_refs: frozenset[str] = frozenset()) -> Any:
            if isinstance(node, list):
                return [convert(item, active_refs) for item in node]
            if not isinstance(node, dict):
                return node
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                if ref in active_refs:
                    return {"type": "OBJECT"}
                definition = definitions.get(ref.removeprefix("#/$defs/"))
                if isinstance(definition, dict):
                    merged = deepcopy(definition)
                    merged.update({key: value for key, value in node.items() if key != "$ref"})
                    return convert(merged, active_refs | {ref})
            result: Dict[str, Any] = {}
            for key, value in node.items():
                if key not in supported_keys:
                    continue
                if key == "type":
                    if isinstance(value, str):
                        result[key] = type_names.get(value, value.upper())
                    elif isinstance(value, list):
                        result[key] = [type_names.get(item, item.upper()) for item in value]
                elif key == "properties" and isinstance(value, dict):
                    result[key] = {name: convert(child, active_refs) for name, child in value.items()}
                elif key == "items" and isinstance(value, dict):
                    result[key] = convert(value, active_refs)
                elif key in supported_keys:
                    result[key] = value
            return result

        converted = convert(schema)
        return converted if isinstance(converted, dict) else {}

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
                failure_category="rate_limit",
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
                failure_category="timeout" if request.simulate_failure == "timeout" else "server_error",
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
                failure_category="missing_credentials",
                latency_ms=round(latency_ms, 2),
            )

        endpoint = f"{self.base_url}/models/{self.default_model}:generateContent"

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
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
                    failure_category=self.classify_http_status(resp.status_code),
                    latency_ms=round(latency_ms, 2),
                )

            data = resp.json()
            usage = data.get("usageMetadata", {})
            prompt_tokens, completion_tokens, total_tokens, cost = self._usage_metrics(
                data, request.prompt, ""
            )
            candidates = data.get("candidates", [])
            if not candidates:
                prompt_feedback = data.get("promptFeedback", {})
                block_reason = (
                    str(prompt_feedback.get("blockReason") or "").upper()
                    if isinstance(prompt_feedback, dict)
                    else ""
                )
                blocked = block_reason in {
                    "SAFETY",
                    "BLOCKLIST",
                    "PROHIBITED_CONTENT",
                    "IMAGE_SAFETY",
                }
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message=(
                        "Gemini response was blocked by its safety filters."
                        if blocked
                        else "Gemini returned no candidates in response."
                    ),
                    failure_category=("safety_refusal" if blocked else "malformed_output"),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=round(latency_ms, 2),
                )

            content_parts = candidates[0].get("content", {}).get("parts", [])
            text_out = "".join(part.get("text", "") for part in content_parts)

            prompt_tokens, completion_tokens, total_tokens, cost = self._usage_metrics(
                data, request.prompt, text_out
            )

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
        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="Gemini request timed out.",
                failure_category="timeout",
                latency_ms=round(latency_ms, 2),
            )
        except httpx.NetworkError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=self._sanitize_error(
                    f"Gemini connection failed ({type(e).__name__}): [REDACTED]"
                ),
                failure_category="connection_error",
                latency_ms=round(latency_ms, 2),
            )
        except (ValueError, TypeError, AttributeError) as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=f"Gemini response parsing failed ({type(e).__name__}).",
                failure_category="malformed_output",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=f"Gemini provider error ({type(e).__name__}).",
                failure_category="provider_error",
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
                failure_category="rate_limit" if request.simulate_failure == "rate_limit" else "server_error",
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
                failure_category="malformed_output",
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
                failure_category="missing_credentials",
                latency_ms=round(latency_ms, 2),
            )

        endpoint = f"{self.base_url}/models/{self.default_model}:generateContent"

        schema_prompt = (
            f"{request.prompt}\n\n"
            "Return only one JSON object that conforms exactly to this schema, with no extra keys:\n"
            f"{json.dumps(request.response_schema, ensure_ascii=False, separators=(',', ':'))}"
        )

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": schema_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "responseMimeType": "application/json",
                "responseSchema": self._gemini_schema(request.response_schema),
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
                    failure_category=self.classify_http_status(resp.status_code),
                    latency_ms=round(latency_ms, 2),
                )

            data = resp.json()
            usage = data.get("usageMetadata", {})
            prompt_tokens, completion_tokens, total_tokens, cost = self._usage_metrics(
                data, schema_prompt, ""
            )
            candidates = data.get("candidates", [])
            if not candidates:
                prompt_feedback = data.get("promptFeedback", {})
                block_reason = (
                    str(prompt_feedback.get("blockReason") or "").upper()
                    if isinstance(prompt_feedback, dict)
                    else ""
                )
                blocked = block_reason in {
                    "SAFETY",
                    "BLOCKLIST",
                    "PROHIBITED_CONTENT",
                    "IMAGE_SAFETY",
                }
                return AIResponse(
                    text="",
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message=(
                        "Gemini structured output was blocked by its safety filters."
                        if blocked
                        else "Gemini returned no candidates."
                    ),
                    failure_category=("safety_refusal" if blocked else "malformed_output"),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=round(latency_ms, 2),
                )

            candidate = candidates[0]
            raw_text = "".join(
                part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
            )
            finish_reason = str(candidate.get("finishReason") or "").upper()
            if finish_reason and finish_reason not in {"STOP", "FINISH_REASON_UNSPECIFIED"}:
                if finish_reason == "MAX_TOKENS":
                    finish_error = "Gemini reached max output tokens before completing structured JSON."
                elif finish_reason in {
                    "SAFETY",
                    "BLOCKLIST",
                    "PROHIBITED_CONTENT",
                    "IMAGE_SAFETY",
                    "SPII",
                    "RECITATION",
                }:
                    finish_error = "Gemini structured output was blocked by its safety filters."
                else:
                    finish_error = f"Gemini structured output ended with finish reason {finish_reason}."
                return AIResponse(
                    text="",
                    structured_data=None,
                    provider=self.provider_id,
                    model=self.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message=finish_error,
                    failure_category=(
                        "malformed_output" if finish_reason == "MAX_TOKENS" else
                        "safety_refusal"
                        if finish_reason in {
                            "SAFETY",
                            "BLOCKLIST",
                            "PROHIBITED_CONTENT",
                            "IMAGE_SAFETY",
                            "SPII",
                            "RECITATION",
                        }
                        else "provider_error"
                    ),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=round(latency_ms, 2),
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

            prompt_tokens, completion_tokens, total_tokens, cost = self._usage_metrics(
                data, schema_prompt, raw_text
            )

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
                    failure_category="malformed_output",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=round(latency_ms, 2),
                )

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
        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="Gemini request timed out.",
                failure_category="timeout",
                latency_ms=round(latency_ms, 2),
            )
        except httpx.NetworkError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=self._sanitize_error(
                    f"Gemini connection failed ({type(e).__name__}): [REDACTED]"
                ),
                failure_category="connection_error",
                latency_ms=round(latency_ms, 2),
            )
        except (ValueError, TypeError, AttributeError) as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=f"Gemini response parsing failed ({type(e).__name__}).",
                failure_category="malformed_output",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=f"Gemini provider error ({type(e).__name__}).",
                failure_category="provider_error",
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
            preferred_provider="gemini",
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
