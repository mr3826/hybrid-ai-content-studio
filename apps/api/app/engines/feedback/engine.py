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
from app.engines.feedback.synthesizer import FeedbackSynthesizer


class FeedbackEngine(BaseEngine):
    """Human-Approved Feedback Engine.
    Closed feedback loop that analyzes publication performance lessons,
    generates proposed brand memory and editorial rule adjustments,
    and enforces explicit human approval before any self-modification.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).parent
        super().__init__(engine_dir=engine_dir)
        self.synthesizer = FeedbackSynthesizer(rules=self.rules)

    @property
    def version(self) -> str:
        return self.manifest.version

    def validate_config(self) -> None:
        """Validates that engine rules are loaded and invariants are respected."""
        if not self.rules:
            raise ValueError(f"FeedbackEngine rules could not be loaded from {self.engine_dir / 'rules.yaml'}")
        if self.rules.get("auto_apply", False) is not False:
            raise ValueError("Invariant violation: FeedbackEngine cannot have auto_apply enabled. Human approval required.")

    def health(self) -> EngineHealth:
        """Returns engine health status."""
        has_rules = self.rules is not None and len(self.rules) > 0
        auto_apply_safe = self.rules.get("auto_apply") is False
        healthy = has_rules and auto_apply_safe
        return EngineHealth(
            status="healthy" if healthy else "degraded",
            message="Feedback Engine operational with human quality gate intact.",
            details={
                "has_rules": has_rules,
                "engine_version": self.version,
                "auto_apply_disabled": auto_apply_safe,
                "allowed_lesson_types": self.rules.get("allowed_lesson_types", []),
            },
        )

    async def run(self, context: EngineContext, session=None) -> EngineResult:
        """Evaluates snapshots and scripts in context and returns generated lesson proposals."""
        started_at = datetime.now(timezone.utc)
        snapshots = context.parameters.get("snapshots", [])
        content_items_map = context.parameters.get("content_items_map", {})
        scripts_map = context.parameters.get("scripts_map", {})
        brand_profile = context.parameters.get("brand_profile", {})

        generated_lessons: List[Dict[str, Any]] = []
        for snap in snapshots:
            item_id = snap.get("content_item_id")
            content_item = content_items_map.get(item_id)
            script_data = scripts_map.get(item_id)
            lessons = self.synthesizer.evaluate_item_performance(
                snapshot=snap,
                content_item=content_item,
                script_data=script_data,
                brand_profile=brand_profile,
            )
            generated_lessons.extend(lessons)

        ended_at = datetime.now(timezone.utc)
        return EngineResult(
            engine_id=self.manifest.id,
            engine_version=self.manifest.version,
            run_id=context.run_id,
            success=True,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            summary=f"Synthesized {len(generated_lessons)} feedback lessons from {len(snapshots)} snapshots.",
            input_count=len(snapshots),
            output_count=len(generated_lessons),
            outputs=generated_lessons,
            rules_version=self.rules.get("rules_version", "1.0.0"),
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Dry run: generates proposals without any persistence."""
        result = await self.run(context)
        result.summary = f"[Dry-Run] {result.summary}"
        return result

    def explain(self, result_id: str) -> EngineExplanation:
        """Explains the data-driven reasoning and human-gate policy for lesson generation."""
        return EngineExplanation(
            result_id=result_id,
            summary="Creator-Guided Closed Loop Learning Proposal: Evaluates 3s hook drop and engagement benchmarks with mandatory human approval before applying to Brand DNA.",
            factors=[
                {"factor": "Hook Retention Benchmarks", "weight": 0.40, "description": f"Evaluated against critical drop threshold ({self.rules.get('hook_retention_critical_threshold_pct')}%) and viral threshold ({self.rules.get('hook_retention_viral_threshold_pct')}%)."},
                {"factor": "Engagement Rate Thresholds", "weight": 0.35, "description": f"Evaluated interactions against low threshold ({self.rules.get('engagement_rate_critical_threshold_pct')}%) and high-affinity threshold ({self.rules.get('engagement_rate_strong_threshold_pct')}%)."},
                {"factor": "Non-Negotiable Human Gate", "weight": 0.25, "description": "Auto-apply is permanently disabled; explicit creator approval is mandatory before any Brand DNA or rule alteration."},
            ],
        )
