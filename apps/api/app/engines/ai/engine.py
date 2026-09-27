import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.engines.ai.adapters.mock import MockAIAdapter
from app.repositories.ai_repository import AIRepository


class AIProviderEngine(BaseEngine):
    """Centralized pluggable AI Provider Engine.

    Manages LLM provider adapters (Gemini primary, Qwen fallback, Mock for testing),
    enforces technical/schema fallback rules, calculates token usage and cost,
    and logs immutable invocation telemetry.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)

        cost_rates = self.rules.get("cost_rates", {})
        gemini_rates = cost_rates.get("gemini", {"prompt_per_million": 0.10, "completion_per_million": 0.40})
        qwen_rates = cost_rates.get("qwen", {"prompt_per_million": 0.40, "completion_per_million": 1.20})
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

        self.mock_adapter = MockAIAdapter(cost_rates=mock_rates)

    def validate_config(self) -> None:
        """Validate engine configuration or rules."""
        if not self.rules:
            raise ValueError("AIProviderEngine rules cannot be empty.")
        if "primary_provider" not in self.rules:
            raise ValueError("primary_provider must be defined in AI rules.")

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
        primary_configured = bool(settings.GEMINI_API_KEY)
        fallback_configured = bool(settings.QWEN_API_KEY)
        if primary_configured and fallback_configured:
            status = "healthy"
            msg = "Gemini and Qwen adapters configured."
        elif primary_configured or fallback_configured:
            status = "degraded"
            msg = f"Partial configuration (Gemini: {primary_configured}, Qwen: {fallback_configured})."
        else:
            status = "degraded"
            msg = "No external AI API keys configured (set in environment or enable AI_MOCK_MODE)."
        return EngineHealth(
            status=status,
            message=msg,
            details={
                "primary_configured": primary_configured,
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
        if preferred == "qwen":
            return self.qwen_adapter
        return self.gemini_adapter

    def _get_fallback_adapter(self) -> BaseAIAdapter:
        if settings.AI_MOCK_MODE:
            # Secondary mock adapter configured to succeed when fallback occurs
            adapter = MockAIAdapter()
            adapter.provider_id = "qwen-mock-fallback"
            adapter.default_model = "mock-qwen-fallback-model"
            return adapter
        return self.qwen_adapter

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
            "server error", "service unavailable", "timed out",
            "technical failure"
        ]
        return any(ind in lower for ind in indicators)

    async def _log_telemetry(self, response: AIResponse, prompt_text: str, session: Optional[AsyncSession] = None) -> None:
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
        primary = self._get_primary_adapter(request.preferred_provider)
        resp = await primary.generate_text(request)

        if not resp.success and request.allow_fallback and self.rules.get("fallback_enabled", True):
            if self._is_technical_or_schema_failure(resp.error_message):
                fallback = self._get_fallback_adapter()
                fb_request = request.model_copy(update={"simulate_failure": None})
                fb_resp = await fallback.generate_text(fb_request)
                if fb_resp.success:
                    fb_resp.fallback_used = True
                    fb_resp.fallback_reason = resp.error_message
                    fb_resp.primary_provider = primary.provider_id
                    fb_resp.primary_error = resp.error_message
                    resp = fb_resp

        await self._log_telemetry(resp, request.prompt, session)
        return resp

    async def generate_structured(
        self,
        request: StructuredGenerationRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Execute schema-enforced structured generation with technical fallback."""
        primary = self._get_primary_adapter(request.preferred_provider)
        resp = await primary.generate_structured(request)

        if not resp.success and request.allow_fallback and self.rules.get("fallback_enabled", True):
            if self._is_technical_or_schema_failure(resp.error_message):
                fallback = self._get_fallback_adapter()
                fb_request = request.model_copy(update={"simulate_failure": None})
                fb_resp = await fallback.generate_structured(fb_request)
                if fb_resp.success:
                    fb_resp.fallback_used = True
                    fb_resp.fallback_reason = resp.error_message
                    fb_resp.primary_provider = primary.provider_id
                    fb_resp.primary_error = resp.error_message
                    resp = fb_resp

        await self._log_telemetry(resp, request.prompt, session)
        return resp

    async def analyze(
        self,
        request: AnalyzeRequest,
        session: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Audit and analyze content with technical fallback."""
        primary = self._get_primary_adapter(request.preferred_provider)
        resp = await primary.analyze(request)

        if not resp.success and request.allow_fallback and self.rules.get("fallback_enabled", True):
            if self._is_technical_or_schema_failure(resp.error_message):
                fallback = self._get_fallback_adapter()
                fb_request = request.model_copy(update={"simulate_failure": None})
                fb_resp = await fallback.analyze(fb_request)
                if fb_resp.success:
                    fb_resp.fallback_used = True
                    fb_resp.fallback_reason = resp.error_message
                    fb_resp.primary_provider = primary.provider_id
                    fb_resp.primary_error = resp.error_message
                    resp = fb_resp

        await self._log_telemetry(resp, request.content, session)
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
        return AIProviderStatus(
            mock_mode=settings.AI_MOCK_MODE,
            primary_provider="gemini",
            primary_configured=bool(settings.GEMINI_API_KEY) or settings.AI_MOCK_MODE,
            primary_model=settings.GEMINI_MODEL,
            fallback_provider="qwen",
            fallback_configured=bool(settings.QWEN_API_KEY) or settings.AI_MOCK_MODE,
            fallback_model=settings.QWEN_MODEL,
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

        gemini_health = await self.gemini_adapter.health_check()
        qwen_health = await self.qwen_adapter.health_check()

        overall_status = "healthy"
        if gemini_health["status"] != "healthy" and qwen_health["status"] != "healthy":
            overall_status = "failing"
        elif gemini_health["status"] != "healthy" or qwen_health["status"] != "healthy":
            overall_status = "degraded"

        return EngineHealth(
            status=overall_status,
            message=f"Gemini: {gemini_health['status']} | Qwen: {qwen_health['status']}",
            details={
                "gemini": gemini_health,
                "qwen": qwen_health,
            },
        )

    def explain(self, result_id: str) -> EngineExplanation:
        """Provide audit and decision explainability for the AI provider engine."""
        return EngineExplanation(
            result_id=result_id,
            summary="AI Provider Engine routing policy with technical-only fallback and zero hallucination rules.",
            factors=[
                {
                    "name": "Routing Decision",
                    "description": "Primary calls route to Gemini; technical (429/500/503/timeout) or schema failures failover to Qwen.",
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
