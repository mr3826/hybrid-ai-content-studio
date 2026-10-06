from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.audience.analyzer import AudienceAnalyzer


class AudienceEngine(BaseEngine):
    """Owned Audience Tracking Engine.
    Converts rented social platform impressions into durable, owned audience assets,
    computes subscriber economics (LTV, list value, conversion rates), generates traceable UTM campaigns,
    and attributes audience conversions across platforms.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).parent
        super().__init__(engine_dir=engine_dir)
        self.analyzer = AudienceAnalyzer(rules=self.rules)

    @property
    def version(self) -> str:
        return self.manifest.version

    def validate_config(self) -> None:
        """Validates that engine rules and conversion benchmarks are present."""
        if not self.rules:
            raise ValueError(f"AudienceEngine rules could not be loaded from {self.engine_dir / 'rules.yaml'}")
        if "target_conversion_rate_pct" not in self.rules:
            raise ValueError("AudienceEngine rules must define 'target_conversion_rate_pct'")
        if "default_lead_value_usd" not in self.rules:
            raise ValueError("AudienceEngine rules must define 'default_lead_value_usd'")

    def health(self) -> EngineHealth:
        """Returns engine health status."""
        has_rules = self.rules is not None and len(self.rules) > 0
        healthy = has_rules and "target_conversion_rate_pct" in self.rules
        return EngineHealth(
            status="healthy" if healthy else "degraded",
            message="Owned Audience Tracking Engine operational with subscriber economics & UTM attribution active.",
            details={
                "has_rules": has_rules,
                "engine_version": self.version,
                "target_conversion_rate_pct": self.rules.get("target_conversion_rate_pct"),
                "default_lead_value_usd": self.rules.get("default_lead_value_usd"),
                "supported_magnet_types": self.rules.get("supported_magnet_types", []),
            },
        )

    async def run(self, context: EngineContext, session=None) -> EngineResult:
        """Analyzes lead magnets and conversion records to generate studio audience summary."""
        started_at = datetime.now(timezone.utc)
        magnets = context.parameters.get("magnets", [])
        conversions = context.parameters.get("conversions", [])

        summary_data = self.analyzer.aggregate_summary(magnets=magnets, conversions=conversions)
        ended_at = datetime.now(timezone.utc)

        return EngineResult(
            engine_id=self.manifest.id,
            engine_version=self.manifest.version,
            run_id=context.run_id,
            success=True,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            summary=f"Evaluated {len(magnets)} lead magnets and {len(conversions)} conversion events. Total Signups: {summary_data['total_signups']}, Est. List Value: ${summary_data['estimated_total_list_value_usd']:,.2f}",
            input_count=len(magnets) + len(conversions),
            output_count=1,
            outputs=[summary_data],
            rules_version=self.rules.get("rules_version", "1.0.0"),
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Dry run: calculates audience metrics without saving any state."""
        result = await self.run(context)
        result.summary = f"[Dry-Run] {result.summary}"
        return result

    def explain(self, result_id: str) -> EngineExplanation:
        """Explains audience valuation methodology, attribution model, and conversion benchmarks."""
        target_rate = self.rules.get("target_conversion_rate_pct", 3.0)
        default_lead_val = self.rules.get("default_lead_value_usd", 15.0)
        return EngineExplanation(
            result_id=result_id,
            summary="Owned Audience Valuation & Attribution Model: Converts rented platform views into owned subscriber assets using standard email subscriber LTV economics and UTM tracking.",
            factors=[
                {
                    "factor": "Subscriber Asset Valuation",
                    "weight": 0.40,
                    "description": f"Calculates list asset worth based on per-magnet custom value or default baseline (${default_lead_val:.2f}/lead).",
                },
                {
                    "factor": "Landing Page Conversion Benchmark",
                    "weight": 0.35,
                    "description": f"Evaluates opt-in efficacy against the studio target conversion benchmark ({target_rate:.1f}%).",
                },
                {
                    "factor": "Deterministic UTM Attribution",
                    "weight": 0.25,
                    "description": "Standardizes utm_source, utm_medium, and utm_campaign parameter taxonomy to track conversion provenance back to individual content items.",
                },
            ],
        )
