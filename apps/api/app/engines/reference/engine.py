import time
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
from app.engines.reference.contracts import BenchmarkReport, BenchmarkSignal


class ReferenceEngine(BaseEngine):
    """Reference implementation of a studio feature engine."""

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)
        self._execution_history: Dict[str, BenchmarkReport] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("ReferenceEngine rules cannot be empty.")
        if "thresholds" not in self.rules:
            raise ValueError("ReferenceEngine rules missing 'thresholds' block.")
        if "min_metric_value" not in self.rules["thresholds"]:
            raise ValueError("ReferenceEngine rules missing 'min_metric_value'.")

    def health(self) -> EngineHealth:
        try:
            self.validate_config()
            return EngineHealth(
                status="healthy",
                message="ReferenceEngine configuration is valid and operational.",
                details={"rules_version": self.rules.get("version", "1.0.0")},
            )
        except Exception as e:
            return EngineHealth(
                status="failing",
                message=f"ReferenceEngine health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()

        # Extract sample inputs or parameters
        signals_data = context.parameters.get("signals", [
            {"id": "sig-01", "title": "Inference Latency Run", "metric_value": 45.2, "category": "latency"},
            {"id": "sig-02", "title": "Sub-threshold Noise", "metric_value": 4.1, "category": "noise"},
        ])

        signals = [BenchmarkSignal(**s) for s in signals_data]
        min_val = self.rules.get("thresholds", {}).get("min_metric_value", 10.0)

        reports: List[BenchmarkReport] = []
        rejected_count = 0
        explanations: List[Dict[str, Any]] = []

        for sig in signals:
            passed = sig.metric_value >= min_val
            score = round(min(100.0, sig.metric_value * 2.0), 1)
            reasons = [
                f"Metric {sig.metric_value} >= {min_val}" if passed else f"Metric {sig.metric_value} < {min_val} cutoff"
            ]

            report = BenchmarkReport(
                id=f"rep-{sig.id}",
                signal_id=sig.id,
                score=score,
                passed=passed,
                summary=f"Benchmark evaluated for {sig.title}: {'PASSED' if passed else 'REJECTED'}",
                reasons=reasons,
            )
            reports.append(report)
            self._execution_history[report.id] = report

            if not passed:
                rejected_count += 1

            explanations.append({
                "signal_id": sig.id,
                "score": score,
                "passed": passed,
                "factor": "metric_threshold",
                "value": sig.metric_value,
                "cutoff": min_val,
            })

        duration_ms = int((time.perf_counter() - t0) * 1000)
        end_time = datetime.now(timezone.utc)

        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            success=True,
            started_at=start_time,
            ended_at=end_time,
            duration_ms=duration_ms,
            input_count=len(signals),
            output_count=len(reports) - rejected_count,
            rejected_count=rejected_count,
            error_count=0,
            cost=0.0,
            summary=f"Evaluated {len(signals)} signals: {len(reports) - rejected_count} passed, {rejected_count} rejected.",
            outputs=[r.model_dump() for r in reports],
            explanations=explanations,
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        # Same evaluation logic but flagged as dry run with zero side effects
        context.dry_run = True
        result = await self.run(context)
        result.summary = f"[DRY RUN] {result.summary}"
        return result

    def explain(self, result_id: str) -> EngineExplanation:
        report = self._execution_history.get(result_id)
        if not report:
            return EngineExplanation(
                result_id=result_id,
                summary=f"No execution history found for report '{result_id}'.",
                factors=[],
            )

        min_val = self.rules.get("thresholds", {}).get("min_metric_value", 10.0)
        return EngineExplanation(
            result_id=result_id,
            summary=f"Report {result_id} achieved score {report.score} ({'PASSED' if report.passed else 'REJECTED'}).",
            factors=[
                {
                    "rule": "min_metric_value",
                    "threshold": min_val,
                    "passed": report.passed,
                    "reasons": report.reasons,
                }
            ],
        )
