import asyncio
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError as JSONSchemaValidationError

from app.core.config import settings
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
    AIResponse,
    AIProviderAttempt,
    AIProviderStatus,
)
from app.engines.ai.adapters.base import BaseAIAdapter
from app.engines.ai.adapters.gemini import GeminiAdapter
from app.engines.ai.adapters.mock import MockAIAdapter
from app.repositories.ai_repository import AIRepository


class AIProviderEngine(BaseEngine):
    """Gemini-backed AI engine with a deterministic offline mock adapter."""

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)

        cost_rates = self.rules.get("cost_rates", {})
        gemini_rates = cost_rates.get(
            "gemini", {"prompt_per_million": 0.75, "completion_per_million": 3.75}
        )
        mock_rates = cost_rates.get("mock", {"prompt_per_million": 0.00, "completion_per_million": 0.00})

        self.gemini_adapter = GeminiAdapter(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            cost_rates=gemini_rates,
            timeout_seconds=self.rules.get("timeout_seconds", 30),
        )

        self.mock_adapter = MockAIAdapter(cost_rates=mock_rates)
        self._budget_lock = asyncio.Lock()

    def validate_config(self) -> None:
        """Validate engine configuration or rules."""
        if not self.rules:
            raise ValueError("AIProviderEngine rules cannot be empty.")
        if "gemini" not in self.rules.get("cost_rates", {}):
            raise ValueError("Gemini cost rates must be defined in AI rules.")

    def health(self) -> EngineHealth:
        """Perform active sync health check for BaseEngine contract."""
        if settings.AI_MOCK_MODE:
            return EngineHealth(
                status="healthy",
                message="AI Provider Engine running in Mock Mode (offline deterministic adapters).",
                details={"mode": "mock", "provider": "mock"},
            )
        configured = self._provider_is_configured("gemini")
        status = "healthy" if configured else "degraded"
        msg = (
            "Gemini credentials are configured."
            if configured
            else "Gemini credentials are missing; configure CONTENT_STUDIO_GEMINI or enable mock mode."
        )
        return EngineHealth(
            status=status,
            message=msg,
            details={
                "provider": "gemini",
                "configured": configured,
                "mock_mode": settings.AI_MOCK_MODE,
            },
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Execute without persisting side effects."""
        ctx = context.model_copy(update={"dry_run": True})
        return await self.run(ctx)

    def _get_primary_adapter(self, preferred: Optional[str] = None) -> BaseAIAdapter:
        if settings.AI_MOCK_MODE or preferred == "mock":
            return self.mock_adapter
        if preferred not in (None, "gemini"):
            raise ValueError("Live generation supports Gemini only; select Gemini or Mock.")
        return self.gemini_adapter

    def _provider_is_configured(self, provider: str) -> bool:
        if provider != "gemini":
            return False
        credential = self.gemini_adapter.api_key
        return isinstance(credential, str) and bool(credential.strip())

    def estimate_max_cost(self, request: StructuredGenerationRequest) -> float:
        """Estimate one Gemini request at the configured output-token ceiling."""
        if settings.AI_MOCK_MODE or request.preferred_provider == "mock":
            return 0.0

        primary = self._get_primary_adapter(request.preferred_provider)
        prompt = request.prompt + json.dumps(request.response_schema, separators=(",", ":"))
        prompt_tokens = max(1, math.ceil(len(prompt) / 4))
        return round(
            self._maximum_provider_cost(primary, prompt_tokens, request.max_tokens), 10
        )

    @staticmethod
    def _maximum_provider_cost(
        adapter: BaseAIAdapter, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """Use provider-specific worst-case pricing when estimating budget usage."""
        estimator = getattr(adapter, "calculate_max_cost", None)
        if callable(estimator):
            return float(estimator(prompt_tokens, completion_tokens))
        return adapter.calculate_cost(prompt_tokens, completion_tokens)

    def _estimate_request_cost(self, request: Any, primary: BaseAIAdapter) -> float:
        if settings.AI_MOCK_MODE or getattr(request, "preferred_provider", None) == "mock":
            return 0.0
        if isinstance(request, StructuredGenerationRequest):
            prompt = request.prompt + json.dumps(request.response_schema, separators=(",", ":"))
        elif isinstance(request, TextGenerationRequest):
            prompt = request.prompt
        else:
            prompt = request.content + request.instruction + " ".join(request.criteria)
        prompt_tokens = max(1, math.ceil(len(prompt) / 4))
        max_tokens = getattr(request, "max_tokens", self.rules.get("max_tokens_default", 2048))
        return round(self._maximum_provider_cost(primary, prompt_tokens, max_tokens), 10)

    def _budget_response(
        self,
        request: Any,
        primary: BaseAIAdapter,
        message: str,
    ) -> AIResponse:
        return AIResponse(
            text="",
            provider=primary.provider_id,
            model=primary.default_model,
            task=request.task,
            prompt_version=request.prompt_version,
            success=False,
            error_message=message,
            failure_category="budget_exceeded" if "budget" in message.lower() else "invalid_request",
        )

    @staticmethod
    def _unsupported_provider_response(request: Any, message: str) -> AIResponse:
        return AIResponse(
            text="",
            provider="none",
            model="",
            task=request.task,
            prompt_version=request.prompt_version,
            success=False,
            error_message=message,
            failure_category="invalid_request",
        )

    async def _check_budget(
        self,
        request: Any,
        primary: BaseAIAdapter,
        session: Optional[AsyncSession],
    ) -> Optional[AIResponse]:
        if session is None:
            return None

        estimate = self._estimate_request_cost(request, primary)
        repo = AIRepository(session)
        daily_spend = await repo.get_daily_spend()
        daily_limit = settings.MAX_AI_COST_PER_DAY
        if daily_spend + estimate > daily_limit:
            return self._budget_response(
                request,
                primary,
                f"Daily AI budget would be exceeded (current ${daily_spend:.4f}, "
                f"estimated maximum ${estimate:.4f}, limit ${daily_limit:.2f}).",
            )

        project_id = request.metadata.get("project_id") if isinstance(request.metadata, dict) else None
        if project_id:
            spend_override = request.metadata.get("project_spend_usd")
            if isinstance(spend_override, (int, float)) and spend_override >= 0:
                project_spend = float(spend_override)
            else:
                project_spend = await repo.get_project_spend(str(project_id))
            project_limit = settings.MAX_GENERATION_COST_PER_PROJECT
            if project_spend + estimate > project_limit:
                return self._budget_response(
                    request,
                    primary,
                    f"Content-family AI budget would be exceeded (current ${project_spend:.4f}, "
                    f"estimated maximum ${estimate:.4f}, limit ${project_limit:.2f}).",
                )
        return None

    def _validate_structured_response(
        self, request: StructuredGenerationRequest, response: AIResponse
    ) -> AIResponse:
        if not response.success:
            return response
        if response.structured_data is None:
            response.success = False
            response.error_message = "Schema validation error: provider returned no structured JSON object."
            response.failure_category = "output_schema_validation"
            return response
        try:
            Draft202012Validator.check_schema(request.response_schema)
        except SchemaError as exc:
            response.success = False
            response.error_message = f"Invalid response schema at {'.'.join(str(part) for part in exc.absolute_path)}."
            response.failure_category = "invalid_request"
            return response
        try:
            Draft202012Validator(request.response_schema).validate(response.structured_data)
        except JSONSchemaValidationError as exc:
            path = ".".join(str(part) for part in exc.absolute_path) or "response"
            validator = str(exc.validator or "contract")
            detail = f"Schema validation error at {path} ({validator})."
            if validator == "required" and isinstance(exc.instance, dict):
                missing = [key for key in exc.validator_value if key not in exc.instance]
                if missing:
                    detail += " Missing required field(s): " + ", ".join(map(str, missing)) + "."
            elif validator == "additionalProperties":
                detail += " The response included fields outside the contract."
            elif validator == "enum":
                detail += " The response used a value outside the allowed choices."
            response.success = False
            response.error_message = detail
            response.failure_category = "output_schema_validation"
        return response

    @staticmethod
    def _provider_attempt(response: AIResponse) -> AIProviderAttempt:
        return AIProviderAttempt(
            provider=response.provider,
            model=response.model,
            success=response.success,
            failure_category=response.failure_category,
            error_message=response.error_message,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            cost=response.cost,
            latency_ms=response.latency_ms,
        )

    async def _log_telemetry(
        self,
        response: AIResponse,
        prompt_text: str,
        session: Optional[AsyncSession] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if session is None:
            return
        try:
            repo = AIRepository(session)
            prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
            await repo.log_invocation(
                provider=response.provider,
                model=response.model,
                task=response.task,
                prompt_version=response.prompt_version,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens,
                cost=response.cost,
                latency_ms=response.latency_ms,
                success=response.success,
                error_message=response.error_message,
                fallback_used=response.fallback_used,
                fallback_reason=response.fallback_reason,
                primary_provider=response.primary_provider,
                primary_error=response.primary_error,
                prompt_hash=prompt_hash,
                extra_metadata={
                    key: metadata[key]
                    for key in ("project_id", "content_item_id", "operation")
                    if metadata and key in metadata and isinstance(metadata[key], (str, int))
                }
                | {
                    "primary_model": response.primary_model,
                    "primary_failure_category": response.primary_failure_category,
                    "provider_attempts": [
                        attempt.model_dump(mode="json")
                        for attempt in response.provider_attempts
                    ],
                },
            )
        except Exception:
            # Telemetry logging must never crash the primary execution flow
            pass

    async def _execute_provider_request(
        self,
        request: Any,
        primary: BaseAIAdapter,
        session: Optional[AsyncSession],
        prompt_text: str,
        method_name: str,
        *,
        validate_structured: bool = False,
    ) -> AIResponse:
        budget_response = await self._check_budget(request, primary, session)
        if budget_response is not None:
            await self._log_telemetry(
                budget_response, prompt_text, session, request.metadata
            )
            return budget_response

        response = await getattr(primary, method_name)(request)
        if validate_structured:
            response = self._validate_structured_response(request, response)

        response.provider_attempts = [self._provider_attempt(response)]
        await self._log_telemetry(
            response, prompt_text, session, request.metadata
        )
        return response

    async def generate_text(
        self,
        request: TextGenerationRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Execute one text-generation request through Gemini or the offline mock."""
        async with self._budget_lock:
            try:
                primary = self._get_primary_adapter(request.preferred_provider)
            except ValueError as exc:
                return self._unsupported_provider_response(request, str(exc))
            return await self._execute_provider_request(
                request, primary, session, request.prompt, "generate_text"
            )

    async def generate_structured(
        self,
        request: StructuredGenerationRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Execute one schema-enforced request through Gemini or the offline mock."""
        async with self._budget_lock:
            try:
                primary = self._get_primary_adapter(request.preferred_provider)
            except ValueError as exc:
                return self._unsupported_provider_response(request, str(exc))
            try:
                Draft202012Validator.check_schema(request.response_schema)
            except SchemaError as exc:
                return AIResponse(
                    text="",
                    provider=primary.provider_id,
                    model=primary.default_model,
                    task=request.task,
                    prompt_version=request.prompt_version,
                    success=False,
                    error_message=(
                        "Invalid response schema at "
                        f"{'.'.join(str(part) for part in exc.absolute_path)}."
                    ),
                    failure_category="invalid_request",
                )
            return await self._execute_provider_request(
                request,
                primary,
                session,
                request.prompt,
                "generate_structured",
                validate_structured=True,
            )

    async def analyze(
        self,
        request: AnalyzeRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Analyze content through Gemini or the offline mock."""
        async with self._budget_lock:
            try:
                primary = self._get_primary_adapter(request.preferred_provider)
            except ValueError as exc:
                return self._unsupported_provider_response(request, str(exc))
            prompt_text = request.content + "\n" + request.instruction
            return await self._execute_provider_request(
                request, primary, session, prompt_text, "analyze"
            )

    async def get_status(self, session: Optional[AsyncSession] = None) -> AIProviderStatus:
        """Retrieve operational health, model settings, and budget usage."""
        daily_spend = 0.0
        if session is not None:
            try:
                repo = AIRepository(session)
                daily_spend = await repo.get_daily_spend()
            except Exception:
                daily_spend = 0.0

        daily_limit = settings.MAX_AI_COST_PER_DAY
        # Keep the fallback fields in the response for API compatibility with
        # existing clients; new requests have no fallback route.
        return AIProviderStatus(
            mock_mode=settings.AI_MOCK_MODE,
            primary_provider="gemini",
            primary_configured=self._provider_is_configured("gemini"),
            primary_model=settings.GEMINI_MODEL,
            fallback_provider="none",
            fallback_configured=False,
            fallback_model="",
            fallback_enabled=False,
            daily_spend_today=round(daily_spend, 4),
            daily_budget_limit=daily_limit,
            budget_exceeded=daily_spend >= daily_limit,
        )

    async def run(self, context: EngineContext) -> EngineResult:
        """Run engine invocation implementing BaseEngine contract."""
        start_time = datetime.now(timezone.utc)
        params = context.parameters or {}
        task = params.get("task", "generate_text")
        prompt = params.get("prompt", "Benchmark test prompt for Studio AI Provider")
        dry_run = context.dry_run

        req = TextGenerationRequest(
            prompt=prompt,
            task=task,
            prompt_version=params.get("prompt_version", "1.0.0"),
            preferred_provider=params.get("preferred_provider"),
            simulate_failure=params.get("simulate_failure"),
        )

        resp = await self.generate_text(req)

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        return EngineResult(
            engine_id=self.id,
            engine_version=self.manifest.version,
            rules_version=self.rules.get("version", "1.0.0"),
            run_id=context.run_id,
            success=resp.success,
            started_at=start_time,
            ended_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            input_count=1,
            output_count=1 if resp.success else 0,
            cost=resp.cost,
            summary=f"Processed task '{task}' via {resp.provider} ({resp.model})",
            outputs=[resp.model_dump()],
            errors=[resp.error_message] if resp.error_message else [],
            explanations=[
                {
                    "provider": resp.provider,
                    "model": resp.model,
                    "fallback_used": resp.fallback_used,
                    "fallback_reason": resp.fallback_reason,
                    "tokens": resp.total_tokens,
                    "cost": resp.cost,
                    "dry_run": dry_run,
                }
            ],
        )

    async def health_check(self) -> EngineHealth:
        """Report Gemini configuration without making a provider request."""
        if settings.AI_MOCK_MODE:
            return EngineHealth(
                status="healthy",
                message="AI Provider Engine running in Mock Mode (offline deterministic adapters).",
                details={"mode": "mock", "provider": "mock"},
            )
        gemini = await self.gemini_adapter.health_check()

        return EngineHealth(
            status=gemini["status"],
            message=gemini["message"],
            details={"gemini": gemini},
        )

    def explain(self, result_id: str) -> EngineExplanation:
        """Provide audit and decision explainability for the AI provider engine."""
        return EngineExplanation(
            result_id=result_id,
            summary="AI Provider Engine provides Gemini structured generation with evidence constraints and a deterministic offline mock mode.",
            factors=[
                {
                    "name": "Provider",
                    "description": "Live requests use Gemini; mock mode uses deterministic local output.",
                },
                {
                    "name": "Factual Integrity Invariant",
                    "description": "One live Gemini attempt is made; failures never route to another provider or bypass evidence checks.",
                },
                {
                    "name": "Budget Gate",
                    "description": f"Daily AI spend cap enforced at ${settings.MAX_AI_COST_PER_DAY:.2f} USD.",
                },
                {
                    "name": "Zero Secret Invariant",
                    "description": "API keys are never stored in invocation records or returned in API responses.",
                },
            ],
        )
