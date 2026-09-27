import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.originality.contracts import PlanEvaluationResult
from app.repositories.originality_repository import (
    SUPPORTED_ORIGINALITY_TYPES,
    GENERIC_SUMMARY_INDICATORS,
    OriginalityRepository,
)


class OriginalityEngine(BaseEngine):
    """Originality & Contribution Engine.

    Enforces that every content topic must explicitly answer: 'What are WE adding?'
    Blocks generic news summaries from proceeding into the Script Studio.
    Provides reproducible test harness schemas for the Experiment Workspace.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("OriginalityEngine rules cannot be empty.")
        if "supported_originality_types" not in self.rules:
            raise ValueError("supported_originality_types must be defined in originality rules.")

    def health(self) -> EngineHealth:
        return EngineHealth(
            status="healthy",
            message="Originality Engine operational with 12 contribution types and generic summary gate.",
            details={
                "supported_types_count": len(self.rules.get("supported_originality_types", [])),
                "block_generic_summary": self.rules.get("block_generic_summary", True),
                "min_what_we_add_length": self.rules.get("min_what_we_add_length", 15),
            },
        )

    def evaluate_originality(
        self, topic: str, originality_type: str, what_are_we_adding: str
    ) -> PlanEvaluationResult:
        """Evaluate if an angle adds genuine channel contribution or is a generic summary."""
        types = self.rules.get("supported_originality_types", SUPPORTED_ORIGINALITY_TYPES)
        indicators = self.rules.get("generic_summary_indicators", GENERIC_SUMMARY_INDICATORS)
        min_length = self.rules.get("min_what_we_add_length", 15)

        lower_type = (originality_type or "").lower().strip()
        lower_adding = (what_are_we_adding or "").lower().strip()

        # Check 1: Supported originality type
        if lower_type not in types:
            return PlanEvaluationResult(
                is_ready=False,
                is_generic_summary=True,
                status="not_ready",
                rejection_reason=f"Unsupported originality type '{originality_type}'. Must be one of the 12 verified studio formats.",
                confidence_score=40.0,
                originality_type=originality_type,
                what_are_we_adding=what_are_we_adding,
            )

        # Check 2: Minimum substantive contribution length
        if len(lower_adding) < min_length:
            return PlanEvaluationResult(
                is_ready=False,
                is_generic_summary=True,
                status="not_ready",
                rejection_reason=f"Answer to 'What are WE adding?' is too brief ({len(lower_adding)} chars). Provide a concrete test, benchmark, or synthesis.",
                confidence_score=50.0,
                originality_type=originality_type,
                what_are_we_adding=what_are_we_adding,
            )

        # Check 3: Generic summary indicator strings
        for ind in indicators:
            if ind.lower() in lower_adding:
                return PlanEvaluationResult(
                    is_ready=False,
                    is_generic_summary=True,
                    status="not_ready",
                    rejection_reason=f"Generic summary detected ('{ind}'). Studio rule: Generic summaries default to NOT READY.",
                    confidence_score=45.0,
                    originality_type=originality_type,
                    what_are_we_adding=what_are_we_adding,
                )

        # Passed all gate checks!
        return PlanEvaluationResult(
            is_ready=True,
            is_generic_summary=False,
            status="needs_review",
            confidence_score=90.0,
            originality_type=originality_type,
            what_are_we_adding=what_are_we_adding,
        )

    def propose_original_angles(self, topic: str, summary: str = "") -> List[Dict[str, Any]]:
        """Generate 3 concrete original contribution angles for an opportunity topic."""
        return [
            {
                "originality_type": "benchmark",
                "what_are_we_adding": f"Empirical side-by-side benchmark comparing token throughput and memory saturation on local hardware for '{topic}'.",
                "why_it_matters": "Audiences need real hardware metrics before purchasing or deploying local models.",
                "suggested_experiments": [
                    {
                        "title": "Throughput and Latency Test",
                        "method": "Execute 5 runs measuring tokens per second with Ollama / llama.cpp across context window sizes.",
                    }
                ],
            },
            {
                "originality_type": "failure_analysis",
                "what_are_we_adding": f"Stress-testing edge cases and documenting failure modes when running '{topic}' under constrained VRAM.",
                "why_it_matters": "Exposing where tools fail saves viewers hours of troubleshooting and establishes channel authority.",
                "suggested_experiments": [
                    {
                        "title": "OOM and Quantization Degradation Boundary",
                        "method": "Identify exact context size where unified memory spills to SSD swap.",
                    }
                ],
            },
            {
                "originality_type": "practical_tutorial",
                "what_are_we_adding": f"End-to-end reproducible terminal setup guide and configuration scripts for '{topic}'.",
                "why_it_matters": "Provides immediate tactical utility that viewers can replicate in their own local setup.",
                "suggested_experiments": [
                    {
                        "title": "Clean Install Script Validation",
                        "method": "Run install steps from scratch in an isolated container and record execution logs.",
                    }
                ],
            },
        ]

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = datetime.now(timezone.utc)
        params = context.parameters or {}
        topic = params.get("topic", "Local DeepSeek Inference on M4 Max")
        originality_type = params.get("originality_type", "benchmark")
        what_we_add = params.get("what_are_we_adding", "Benchmarking token throughput and memory bandwidth under 32k context.")

        evaluation = self.evaluate_originality(topic, originality_type, what_we_add)
        angles = self.propose_original_angles(topic)

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        return EngineResult(
            engine_id=self.id,
            engine_version=self.manifest.version,
            rules_version=self.rules_version,
            run_id=context.run_id,
            success=True,
            started_at=start_time,
            ended_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            input_count=1,
            output_count=len(angles),
            summary=f"Evaluated originality for '{topic}': status={evaluation.status}, is_ready={evaluation.is_ready}",
            outputs=[{
                "evaluation": evaluation.model_dump(),
                "proposed_angles": angles,
            }],
            explanations=[{
                "is_generic_summary": evaluation.is_generic_summary,
                "rejection_reason": evaluation.rejection_reason,
                "confidence_score": evaluation.confidence_score,
            }],
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        ctx = context.model_copy(update={"dry_run": True})
        return await self.run(ctx)

    def explain(self, target_id: str) -> EngineExplanation:
        return EngineExplanation(
            result_id=target_id,
            summary="Originality Engine enforces 'What are WE adding?' by requiring topics to contribute net-new empirical value (tests, benchmarks, tutorials, failures) and rejecting generic news summaries.",
            factors=[
                {
                    "name": "Mandatory Channel Contribution",
                    "description": "Every video script must answer 'What are WE adding?' with verifiable data or hands-on testing.",
                },
                {
                    "name": "Generic Summary Quarantine",
                    "description": "Recaps of external articles or aggregation without empirical contribution default to NOT READY.",
                },
                {
                    "name": "Supported Formats",
                    "description": "12 recognized contribution categories including tool_test, benchmark, failure_analysis, practical_tutorial, and cost_comparison.",
                },
                {
                    "name": "Evidence Linkage",
                    "description": "Quantitative experiment measurements link directly to claims in the Evidence Engine provenance graph.",
                },
            ],
        )
