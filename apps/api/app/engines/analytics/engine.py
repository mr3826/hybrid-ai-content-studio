from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.analytics.analyzer import AnalyticsAnalyzer


class AnalyticsEngine(BaseEngine):
    """Engine orchestrating manual publication analytics, hook performance benchmarks,
    platform comparisons, and creator production economics.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).parent
        super().__init__(engine_dir=engine_dir)
        self.analyzer = AnalyticsAnalyzer(rules=self.rules)

    @property
    def version(self) -> str:
        return self.manifest.version

    def validate_config(self) -> None:
        """Validates that engine rules are loaded."""
        if not self.rules:
            raise ValueError(f"AnalyticsEngine rules could not be loaded from {self.engine_dir / 'rules.yaml'}")

    def health(self) -> EngineHealth:
        """Returns engine health status."""
        has_rules = self.rules is not None and len(self.rules) > 0
        return EngineHealth(
            status="healthy" if has_rules else "degraded",
            message="Analytics Engine operational with hook benchmarking and ROI calculation.",
            details={
                "has_rules": has_rules,
                "engine_version": self.version,
                "supported_platforms": self.rules.get("supported_platforms", []),
            },
        )

    async def run(self, context: EngineContext, session=None) -> EngineResult:
        """Runs analytics evaluation on provided context parameters."""
        started_at = datetime.now(timezone.utc)
        snapshots = context.parameters.get("snapshots", [])
        content_items = context.parameters.get("content_items", [])

        # Aggregate platform metrics
        platform_breakdowns = self.analyzer.aggregate_platforms(snapshots)

        # Analyze hooks if provided
        hook_insights = []
        for s in snapshots:
            if s.get("hook_retention_3s_pct") is not None:
                hook_insights.append(
                    self.analyzer.evaluate_hook(
                        content_item_id=s.get("content_item_id", "item-sim"),
                        content_title=s.get("content_title", "Untitled Content"),
                        hook_text=s.get("hook_text", ""),
                        platform=s.get("platform", "youtube"),
                        views=s.get("views", 0),
                        hook_retention_3s_pct=float(s.get("hook_retention_3s_pct", 0.0)),
                        hook_retention_30s_pct=float(s["hook_retention_30s_pct"]) if s.get("hook_retention_30s_pct") is not None else None,
                    ).model_dump()
                )

        ended_at = datetime.now(timezone.utc)
        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            success=True,
            summary=f"Analyzed {len(snapshots)} publication snapshots across {len(platform_breakdowns)} platforms.",
            input_count=len(snapshots),
            output_count=len(platform_breakdowns) + len(hook_insights),
            outputs=[
                {
                    "total_snapshots_analyzed": len(snapshots),
                    "platform_breakdowns": [p.model_dump() for p in platform_breakdowns],
                    "hook_insights": hook_insights,
                }
            ],
        )

    async def dry_run(self, context: EngineContext, session=None) -> EngineResult:
        """Executes a simulation dry run without persisting results."""
        started_at = datetime.now(timezone.utc)
        ended_at = datetime.now(timezone.utc)
        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            success=True,
            summary="[Dry-Run] Simulated analytics evaluation completed.",
            outputs=[
                {
                    "dry_run": True,
                    "message": "Simulated analytics evaluation completed.",
                    "rules_active": list(self.rules.keys()) if self.rules else [],
                }
            ],
        )

    def explain(self, result_id: str) -> EngineExplanation:
        """Returns transparent explanation of analytics benchmarks and scoring formulas."""
        return EngineExplanation(
            engine_id=self.id,
            result_id=result_id,
            summary="Analytics Engine evaluates manual publication metrics, hook retention, and content ROI.",
            factors=[
                {
                    "name": "Engagement Rate",
                    "description": "Calculated as (likes + comments + shares + saves) / total_views * 100. Target >= 5.0%.",
                },
                {
                    "name": "3-Second Hook Retention",
                    "description": "Percentage of viewers holding past 3 seconds. Viral > 80%, Strong > 70%, Dropoff alert < 55%.",
                },
                {
                    "name": "Creator ROI Multiplier",
                    "description": "Total revenue / (AI token cost + Creator labor cost). Profitable >= 1.2x, Break-even >= 0.9x.",
                },
                {
                    "name": "Platform Distribution",
                    "description": "Comparative view volume, engagement, and revenue across YouTube, Facebook, Instagram, TikTok.",
                },
            ],
            recommendations=[
                "Log multiple snapshots over time (24h, 7d, 30d) to measure long-tail algorithmic velocity.",
                "Use high-performing hook text formulas for next video production cycles.",
            ],
        )
