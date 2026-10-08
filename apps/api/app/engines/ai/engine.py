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
    AIProviderStatus,
)
from app.engines.ai.adapters.base import BaseAIAdapter
from app.engines.ai.adapters.gemini import GeminiAdapter
from app.engines.ai.adapters.qwen import QwenAdapter
from app.engines.ai.adapters.openai import OpenAIAdapter
from app.engines.ai.adapters.mock import MockAIAdapter
from app.repositories.ai_repository import AIRepository


class AIProviderEngine(BaseEngine):
    """Centralized pluggable AI Provider Engine.

    Manages LLM provider adapters (Gemini, Qwen, OpenAI, and Mock for testing),
    enforces technical/schema fallback rules, calculates token usage and cost,
    and logs immutable invocation telemetry.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)

        cost_rates = self.rules.get("cost_rates", {})
        gemini_rates = cost_rates.get("gemini", {"prompt_per_million": 0.10, "completion_per_million": 0.40})
        qwen_rates = cost_rates.get("qwen", {"prompt_per_million": 0.40, "completion_per_million": 1.20})
        openai_rates = dict(
            cost_rates.get("openai", {"prompt_per_million": 0.10, "completion_per_million": 0.50})
        )
        if settings.OPENAI_PROMPT_COST_PER_MILLION is not None:
            openai_rates["prompt_per_million"] = settings.OPENAI_PROMPT_COST_PER_MILLION
        if settings.OPENAI_CACHED_PROMPT_COST_PER_MILLION is not None:
            openai_rates["cached_prompt_per_million"] = (
                settings.OPENAI_CACHED_PROMPT_COST_PER_MILLION
            )
        if settings.OPENAI_CACHE_WRITE_PROMPT_COST_PER_MILLION is not None:
            openai_rates["cache_write_prompt_per_million"] = (
                settings.OPENAI_CACHE_WRITE_PROMPT_COST_PER_MILLION
            )
        if settings.OPENAI_COMPLETION_COST_PER_MILLION is not None:
            openai_rates["completion_per_million"] = settings.OPENAI_COMPLETION_COST_PER_MILLION
        mock_rates = cost_rates.get("mock", {"prompt_per_million": 0.00, "completion_per_million": 0.00})

        self.gemini_adapter = GeminiAdapter(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            cost_rates=gemini_rates,
            timeout_seconds=self.rules.get("timeout_seconds", 30),
        )

        self.qwen_adapter = QwenAdapter(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_API_BASE,
            model=settings.QWEN_MODEL,
            cost_rates=qwen_rates,
            timeout_seconds=self.rules.get("timeout_seconds", 30),
        )

        self.openai_adapter = OpenAIAdapter(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            cost_rates=openai_rates,
            timeout_seconds=self.rules.get("timeout_seconds", 30),
            reasoning_effort=settings.OPENAI_REASONING_EFFORT,
        )

        self.mock_adapter = MockAIAdapter(cost_rates=mock_rates)
        self.provider_adapters: Dict[str, BaseAIAdapter] = {
            "gemini": self.gemini_adapter,
            "qwen": self.qwen_adapter,
            "openai": self.openai_adapter,
        }
        self._budget_lock = asyncio.Lock()

    def validate_config(self) -> None:
        """Validate engine configuration or rules."""
        if not self.rules:
            raise ValueError("AIProviderEngine rules cannot be empty.")
        if "primary_provider" not in self.rules:
            raise ValueError("primary_provider must be defined in AI rules.")
        supported_providers = {"gemini", "qwen", "openai"}
        if settings.AI_PRIMARY_PROVIDER not in supported_providers:
            raise ValueError("AI_PRIMARY_PROVIDER must be gemini, qwen, or openai.")
        if settings.AI_FALLBACK_PROVIDER not in supported_providers:
            raise ValueError("AI_FALLBACK_PROVIDER must be gemini, qwen, or openai.")

    def health(self) -> EngineHealth:
        """Perform active sync health check for BaseEngine contract."""
        if settings.AI_MOCK_MODE:
            return EngineHealth(
                status="healthy",
                message="AI Provider Engine running in Mock Mode (offline deterministic adapters).",
                details={
                    "mode": "mock",
                    "primary": "mock",
                    "fallback": "mock",
                },
            )
        primary_provider = settings.AI_PRIMARY_PROVIDER
        fallback_provider = settings.AI_FALLBACK_PROVIDER
        primary_configured = self._provider_is_configured(primary_provider)
        fallback_configured = self._provider_is_configured(fallback_provider)
        if primary_configured and fallback_configured:
            status = "healthy"
            msg = f"{primary_provider} primary and {fallback_provider} fallback adapters configured."
        elif primary_configured or fallback_configured:
            status = "degraded"
            msg = (
                f"Partial configuration ({primary_provider}: {primary_configured}, "
                f"{fallback_provider}: {fallback_configured})."
            )
        else:
            status = "degraded"
            msg = "No external AI API keys configured (set in environment or enable AI_MOCK_MODE)."
        return EngineHealth(
            status=status,
            message=msg,
            details={
                "primary_provider": primary_provider,
                "primary_configured": primary_configured,
                "fallback_provider": fallback_provider,
                "fallback_configured": fallback_configured,
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
        provider = preferred or settings.AI_PRIMARY_PROVIDER or self.rules.get("primary_provider", "gemini")
        try:
            return self.provider_adapters[provider]
        except KeyError as exc:
            raise ValueError(f"Unsupported AI provider: {provider}.") from exc

    def _provider_is_configured(self, provider: str) -> bool:
        if settings.AI_MOCK_MODE:
            return True
        adapter = self.provider_adapters.get(provider)
        return bool(getattr(adapter, "api_key", None))

    def _get_fallback_adapter(self) -> BaseAIAdapter:
        if settings.AI_MOCK_MODE:
            # Secondary mock adapter configured to succeed when fallback occurs
            adapter = MockAIAdapter()
            adapter.provider_id = "qwen-mock-fallback"
            adapter.default_model = "mock-qwen-fallback-model"
            return adapter
        provider = settings.AI_FALLBACK_PROVIDER or self.rules.get("fallback_provider", "qwen")
        try:
            return self.provider_adapters[provider]
        except KeyError as exc:
            raise ValueError(f"Unsupported AI fallback provider: {provider}.") from exc

    def estimate_max_cost(self, request: StructuredGenerationRequest) -> float:
        """Estimate the maximum configured provider cost, including an eligible fallback."""
        if settings.AI_MOCK_MODE or request.preferred_provider == "mock":
            return 0.0

        primary = self._get_primary_adapter(request.preferred_provider)
        prompt = request.prompt + json.dumps(request.response_schema, separators=(",", ":"))
        prompt_tokens = max(1, math.ceil(len(prompt) / 4))
        cost = self._maximum_provider_cost(primary, prompt_tokens, request.max_tokens)
        fallback_enabled = (
            request.allow_fallback
            and settings.AI_FALLBACK_ENABLED
            and self.rules.get("fallback_enabled", True)
        )
        fallback = self._get_fallback_adapter() if fallback_enabled else None
        if fallback and fallback.provider_id != primary.provider_id:
            cost += self._maximum_provider_cost(
                fallback, prompt_tokens, request.max_tokens
            )
        return round(cost, 10)

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
        cost = self._maximum_provider_cost(primary, prompt_tokens, max_tokens)
        fallback_enabled = (
            getattr(request, "allow_fallback", True)
            and settings.AI_FALLBACK_ENABLED
            and self.rules.get("fallback_enabled", True)
        )
        fallback = self._get_fallback_adapter() if fallback_enabled else None
        if fallback and fallback.provider_id != primary.provider_id:
            cost += self._maximum_provider_cost(fallback, prompt_tokens, max_tokens)
        return round(cost, 10)

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
            return response
        try:
            Draft202012Validator.check_schema(request.response_schema)
        except SchemaError as exc:
            response.success = False
            response.error_message = f"Invalid response schema at {'.'.join(str(part) for part in exc.absolute_path)}."
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
        return response

    def _is_technical_or_schema_failure(self, error_msg: Optional[str]) -> bool:
        if not error_msg:
            return False
        lower = error_msg.lower()

        # Check forbidden reasons (do not use fallback to manufacture factual support)
        forbidden = self.rules.get("forbidden_fallback_reasons", [
            "insufficient_evidence", "lack_of_facts", "unsupported_claim", "editorial_rejection"
        ])
        for f in forbidden:
            if f.lower() in lower:
                return False

        # Check technical indicators
        indicators = [
            "429", "500", "502", "503", "504", "408",
            "rate limit", "overloaded", "connection", "timeout",
            "schema parsing", "malformed json", "jsondecodeerror",
            "schema validation error",
            "max output tokens",
            "server error", "service unavailable", "timed out",
            "technical failure"
        ]
        return any(ind in lower for ind in indicators)

    async def _log_telemetry(
        self,
        response: AIResponse,
        prompt_text: str,
        session: Optional[AsyncSession] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not session:
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
                },
            )
        except Exception:
            # Telemetry logging must never crash the primary execution flow
            pass

    async def generate_text(
        self,
        request: TextGenerationRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Execute text generation with primary adapter and technical fallback."""
        async with self._budget_lock:
            primary = self._get_primary_adapter(request.preferred_provider)
            resp = await self._check_budget(request, primary, session)
            if resp is None:
                resp = await primary.generate_text(request)
                fallback_enabled = (
                    request.allow_fallback
                    and settings.AI_FALLBACK_ENABLED
                    and self.rules.get("fallback_enabled", True)
                )
                if not resp.success and fallback_enabled and self._is_technical_or_schema_failure(resp.error_message):
                    fallback = self._get_fallback_adapter()
                    if fallback.provider_id != primary.provider_id:
                        await self._log_telemetry(
                            resp, request.prompt, session, request.metadata
                        )
                        fb_resp = await fallback.generate_text(request.model_copy(update={"simulate_failure": None}))
                        fb_resp.fallback_used = True
                        fb_resp.fallback_reason = resp.error_message
                        fb_resp.primary_provider = primary.provider_id
                        fb_resp.primary_error = resp.error_message
                        if not fb_resp.success:
                            fb_resp.error_message = (
                                f"Primary {primary.provider_id} failed: {resp.error_message}; "
                                f"fallback {fallback.provider_id} failed: {fb_resp.error_message}"
                            )
                        resp = fb_resp
            await self._log_telemetry(resp, request.prompt, session, request.metadata)
            return resp

    async def generate_structured(
        self,
        request: StructuredGenerationRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Execute schema-enforced structured generation with technical fallback."""
        async with self._budget_lock:
            primary = self._get_primary_adapter(request.preferred_provider)
            resp = await self._check_budget(request, primary, session)
            if resp is None:
                resp = self._validate_structured_response(
                    request, await primary.generate_structured(request)
                )
                fallback_enabled = (
                    request.allow_fallback
                    and settings.AI_FALLBACK_ENABLED
                    and self.rules.get("fallback_enabled", True)
                )
                if not resp.success and fallback_enabled and self._is_technical_or_schema_failure(resp.error_message):
                    fallback = self._get_fallback_adapter()
                    if fallback.provider_id != primary.provider_id:
                        await self._log_telemetry(
                            resp, request.prompt, session, request.metadata
                        )
                        fb_resp = await fallback.generate_structured(
                            request.model_copy(update={"simulate_failure": None})
                        )
                        fb_resp = self._validate_structured_response(request, fb_resp)
                        fb_resp.fallback_used = True
                        fb_resp.fallback_reason = resp.error_message
                        fb_resp.primary_provider = primary.provider_id
                        fb_resp.primary_error = resp.error_message
                        if not fb_resp.success:
                            fb_resp.error_message = (
                                f"Primary {primary.provider_id} failed: {resp.error_message}; "
                                f"fallback {fallback.provider_id} failed: {fb_resp.error_message}"
                            )
                        resp = fb_resp
            await self._log_telemetry(resp, request.prompt, session, request.metadata)
            return resp

    async def analyze(
        self,
        request: AnalyzeRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Audit and analyze content with technical fallback."""
        async with self._budget_lock:
            primary = self._get_primary_adapter(request.preferred_provider)
            resp = await self._check_budget(request, primary, session)
            if resp is None:
                resp = await primary.analyze(request)
                fallback_enabled = (
                    request.allow_fallback
                    and settings.AI_FALLBACK_ENABLED
                    and self.rules.get("fallback_enabled", True)
                )
                if not resp.success and fallback_enabled and self._is_technical_or_schema_failure(resp.error_message):
                    fallback = self._get_fallback_adapter()
                    if fallback.provider_id != primary.provider_id:
                        await self._log_telemetry(
                            resp, request.content, session, request.metadata
                        )
                        fb_resp = await fallback.analyze(request.model_copy(update={"simulate_failure": None}))
                        fb_resp.fallback_used = True
                        fb_resp.fallback_reason = resp.error_message
                        fb_resp.primary_provider = primary.provider_id
                        fb_resp.primary_error = resp.error_message
                        if not fb_resp.success:
                            fb_resp.error_message = (
                                f"Primary {primary.provider_id} failed: {resp.error_message}; "
                                f"fallback {fallback.provider_id} failed: {fb_resp.error_message}"
                            )
                        resp = fb_resp
            await self._log_telemetry(resp, request.content, session, request.metadata)
            return resp

    async def get_status(self, session: Optional[AsyncSession] = None) -> AIProviderStatus:
        """Retrieve operational health, model settings, and budget usage."""
        daily_spend = 0.0
        if session:
            try:
                repo = AIRepository(session)
                daily_spend = await repo.get_daily_spend()
            except Exception:
                daily_spend = 0.0

        daily_limit = settings.MAX_AI_COST_PER_DAY
        # Report configured routing even while mock mode temporarily routes calls
        # through the mock adapter. This keeps status useful and stable offline.
        primary = self.provider_adapters[settings.AI_PRIMARY_PROVIDER]
        fallback = self.provider_adapters[settings.AI_FALLBACK_PROVIDER]
        return AIProviderStatus(
            mock_mode=settings.AI_MOCK_MODE,
            primary_provider=primary.provider_id,
            primary_configured=self._provider_is_configured(primary.provider_id),
            primary_model=primary.default_model,
            fallback_provider=fallback.provider_id,
            fallback_configured=self._provider_is_configured(fallback.provider_id),
            fallback_model=fallback.default_model,
            fallback_enabled=settings.AI_FALLBACK_ENABLED,
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
        """Verify health of primary and fallback provider adapters."""
        if settings.AI_MOCK_MODE:
            return EngineHealth(
                status="healthy",
                message="AI Provider Engine running in Mock Mode (offline deterministic adapters).",
                details={
                    "mode": "mock",
                    "primary": "mock",
                    "fallback": "mock",
                },
            )

        health_by_provider = {
            name: await adapter.health_check()
            for name, adapter in self.provider_adapters.items()
        }
        active_providers = [settings.AI_PRIMARY_PROVIDER]
        if settings.AI_FALLBACK_ENABLED and settings.AI_FALLBACK_PROVIDER not in active_providers:
            active_providers.append(settings.AI_FALLBACK_PROVIDER)
        active_statuses = [health_by_provider[name]["status"] for name in active_providers]
        if all(status == "healthy" for status in active_statuses):
            overall_status = "healthy"
        elif any(status == "healthy" for status in active_statuses):
            overall_status = "degraded"
        else:
            overall_status = "failing"
        health_summary = " | ".join(
            f"{name}: {result['status']}" for name, result in health_by_provider.items()
        )

        return EngineHealth(
            status=overall_status,
            message=health_summary,
            details=health_by_provider,
        )

    def explain(self, result_id: str) -> EngineExplanation:
        """Provide audit and decision explainability for the AI provider engine."""
        return EngineExplanation(
            result_id=result_id,
            summary="AI Provider Engine routing policy with technical-only fallback and zero hallucination rules.",
            factors=[
                {
                    "name": "Routing Decision",
                    "description": (
                        f"Primary calls route to {settings.AI_PRIMARY_PROVIDER}; technical "
                        f"(429/500/503/timeout) or schema failures fail over to "
                        f"{settings.AI_FALLBACK_PROVIDER}."
                    ),
                },
                {
                    "name": "Factual Integrity Invariant",
                    "description": "Fallback is strictly prohibited when primary output indicates lack of evidence or factual uncertainty.",
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
