import json
import time
from typing import Any, Dict, Optional
from app.engines.ai.adapters.base import BaseAIAdapter
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
    AIResponse,
)


class MockAIAdapter(BaseAIAdapter):
    """Deterministic offline mock adapter for tests and local development."""

    def __init__(self, cost_rates: Optional[Dict[str, float]] = None):
        super().__init__(
            provider_id="mock",
            default_model="mock-studio-model-v1",
            cost_rates=cost_rates or {"prompt_per_million": 0.0, "completion_per_million": 0.0},
        )

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
                error_message="HTTP 429: Too Many Requests (Rate limit exceeded)",
                latency_ms=latency_ms,
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
                error_message="HTTP 503: Service Unavailable (Model overloaded)",
                latency_ms=latency_ms,
            )

        # Realistic mock text output based on prompt context
        mock_output = (
            f"[Studio AI Generated Response]\n"
            f"Subject Analysis: Response generated for task '{request.task}'.\n"
            f"Key takeaway: Grounding claims with empirical evidence increases viewer trust by 4.2x.\n"
            f"Execution prompt summary: {request.prompt[:120]}..."
        )

        prompt_tokens = max(15, len(request.prompt.split()) * 2)
        completion_tokens = max(30, len(mock_output.split()) * 2)
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculate_cost(prompt_tokens, completion_tokens)
        latency_ms = max(5.0, (time.perf_counter() - start_time) * 1000)

        return AIResponse(
            text=mock_output,
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

    async def generate_structured(self, request: StructuredGenerationRequest) -> AIResponse:
        start_time = time.perf_counter()

        if request.simulate_failure in ("server_error", "rate_limit"):
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=f"Technical failure: {request.simulate_failure}",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        if request.simulate_failure == "schema_error":
            # Return malformed JSON that fails schema validation
            malformed_text = "```json\n{ 'invalid_key': unquoted_string, missing_brace"
            return AIResponse(
                text=malformed_text,
                structured_data=None,
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message="JSONDecodeError: Expecting property name enclosed in double quotes",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Build synthetic structured object matching schema properties if provided
        schema_props = request.response_schema.get("properties", {})
        structured_output: Dict[str, Any] = {}

        for prop_name, prop_spec in schema_props.items():
            prop_type = prop_spec.get("type", "string")
            if prop_type == "string":
                structured_output[prop_name] = f"Mock {prop_name} value"
            elif prop_type in ("integer", "number"):
                structured_output[prop_name] = 85
            elif prop_type == "boolean":
                structured_output[prop_name] = True
            elif prop_type == "array":
                structured_output[prop_name] = [f"Item 1", f"Item 2"]
            else:
                structured_output[prop_name] = {}

        if not structured_output:
            structured_output = {
                "summary": f"Structured result for {request.task}",
                "confidence_score": 0.94,
                "verified": True,
                "items": ["Sample verified fact A", "Sample verified fact B"],
            }

        text_str = json.dumps(structured_output, indent=2)
        prompt_tokens = max(20, len(request.prompt.split()) * 2)
        completion_tokens = max(40, len(text_str.split()) * 2)
        cost = self.calculate_cost(prompt_tokens, completion_tokens)
        latency_ms = max(8.0, (time.perf_counter() - start_time) * 1000)

        return AIResponse(
            text=text_str,
            structured_data=structured_output,
            provider=self.provider_id,
            model=self.default_model,
            task=request.task,
            prompt_version=request.prompt_version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            latency_ms=round(latency_ms, 2),
            success=True,
        )

    async def analyze(self, request: AnalyzeRequest) -> AIResponse:
        start_time = time.perf_counter()

        if request.simulate_failure in ("server_error", "rate_limit"):
            return AIResponse(
                text="",
                provider=self.provider_id,
                model=self.default_model,
                task=request.task,
                prompt_version=request.prompt_version,
                success=False,
                error_message=f"Technical failure: {request.simulate_failure}",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        analysis_data = {
            "instruction": request.instruction,
            "criteria_evaluated": request.criteria or ["accuracy", "brand_alignment", "conciseness"],
            "score": 92.5,
            "passed": True,
            "observations": [
                "Content demonstrates strong technical clarity.",
                "Primary assertions are traceable to cited benchmarks.",
            ],
            "recommendations": [
                "Ensure hardware specs are prominently highlighted in the introductory hook."
            ],
        }

        text_str = json.dumps(analysis_data, indent=2)
        prompt_tokens = max(25, len(request.content.split()) + len(request.instruction.split()))
        completion_tokens = max(35, len(text_str.split()) * 2)
        cost = self.calculate_cost(prompt_tokens, completion_tokens)
        latency_ms = max(10.0, (time.perf_counter() - start_time) * 1000)

        return AIResponse(
            text=text_str,
            structured_data=analysis_data,
            provider=self.provider_id,
            model=self.default_model,
            task=request.task,
            prompt_version=request.prompt_version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            latency_ms=round(latency_ms, 2),
            success=True,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "provider": self.provider_id,
            "model": self.default_model,
            "mode": "mock",
            "message": "Offline deterministic mock adapter operational.",
        }
