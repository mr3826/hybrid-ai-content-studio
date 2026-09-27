import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.core.database import AsyncSessionLocal
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.evidence.contracts import (
    CoverageReport,
    EvidenceEngineInput,
    EvidenceEngineOutput,
    ProvenanceTrace,
)
from app.repositories.evidence_repository import EvidenceRepository


class EvidenceEngine(BaseEngine):
    """Engine responsible for Evidence Graph traversal, provenance verification, and quality gates."""

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("EvidenceEngine rules cannot be empty.")

    def health(self) -> EngineHealth:
        return EngineHealth(
            status="healthy",
            message="EvidenceEngine is operational with evidence provenance graph & coverage gates.",
            details={
                "rules_version": self.rules_version,
                "min_coverage_percent": self.rules.get("coverage_thresholds", {}).get("min_coverage_percent", 85.0),
            },
        )

    def explain(self, target_id: str) -> EngineExplanation:
        return EngineExplanation(
            result_id=target_id,
            summary="Evidence Engine enforces that factual claims are backed by primary/supporting citations or empirical experiments.",
            factors=[
                {"thresholds": self.rules.get("coverage_thresholds", {})},
                {"claim_types": self.rules.get("claim_types", {})},
                {"gate_policy": self.rules.get("gate_policy", {})},
            ],
        )

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = time.time()
        run_id = context.run_id or str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        errors: List[str] = []

        params = context.parameters or {}
        packet_id = params.get("packet_id")
        content_id = params.get("content_id")
        custom_claims = params.get("custom_claims")

        coverage_data: Dict[str, Any] = {}
        traces: List[Dict[str, Any]] = []

        try:
            if custom_claims:
                # In-memory evaluation of custom claims
                total = len(custom_claims)
                factual = sum(1 for c in custom_claims if c.get("claim_type") in ("external_fact", "original_measurement", "derived_conclusion"))
                opinions = sum(1 for c in custom_claims if c.get("claim_type") in ("opinion", "prediction_speculation"))
                primary = sum(1 for c in custom_claims if c.get("source_type") == "primary")
                supporting = sum(1 for c in custom_claims if c.get("source_type") == "supporting")
                tests = sum(1 for c in custom_claims if c.get("claim_type") == "original_measurement")
                overridden = sum(1 for c in custom_claims if c.get("is_overridden"))
                unsupported = max(0, factual - (primary + supporting + tests + overridden))
                pct = round(((primary + supporting + tests + overridden) / factual * 100), 1) if factual > 0 else 100.0
                passed = (unsupported == 0) and (pct >= self.rules.get("coverage_thresholds", {}).get("min_coverage_percent", 85.0))

                coverage_data = {
                    "total_claims": total,
                    "factual_claims": factual,
                    "primary_source_backed": primary,
                    "supporting_source_backed": supporting,
                    "original_test_backed": tests,
                    "opinions_labeled": opinions,
                    "overridden_count": overridden,
                    "unsupported": unsupported,
                    "coverage_percent": pct,
                    "gate_passed": passed,
                }
            else:
                async with AsyncSessionLocal() as session:
                    repo = EvidenceRepository(session)
                    coverage_data = await repo.calculate_coverage(packet_id=packet_id, content_id=content_id)
                    # Pull traces for up to 10 claims
                    claims = await repo.list_claims(packet_id=packet_id, limit=10)
                    for c in claims:
                        trace = await repo.trace_provenance(c.id)
                        traces.append(trace)

        except Exception as e:
            errors.append(f"EvidenceEngine run failed: {str(e)}")

        ended_at = datetime.now(timezone.utc)
        duration_ms = int((time.time() - start_time) * 1000)

        # Gate explanation
        min_cov = self.rules.get("coverage_thresholds", {}).get("min_coverage_percent", 85.0)
        gate_passed = coverage_data.get("gate_passed", False)
        summary = (
            f"Evidence coverage: {coverage_data.get('coverage_percent', 0.0)}% "
            f"({coverage_data.get('factual_claims', 0)} factual claims, {coverage_data.get('unsupported', 0)} unsupported). "
            f"Gate status: {'PASS' if gate_passed else 'BLOCKED (min ' + str(min_cov) + '% required)'}."
        )

        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            rules_version=self.rules_version,
            run_id=run_id,
            success=len(errors) == 0,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            input_count=coverage_data.get("total_claims", 0),
            output_count=len(traces),
            rejected_count=coverage_data.get("unsupported", 0),
            error_count=len(errors),
            summary=summary,
            outputs=[{
                "coverage_report": coverage_data,
                "traces": traces,
            }],
            errors=errors,
            explanations=[{
                "summary": summary,
                "coverage": coverage_data,
                "thresholds": self.rules.get("coverage_thresholds", {}),
            }],
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Simulate evidence coverage checks without persisting overrides or links."""
        return await self.run(context)
