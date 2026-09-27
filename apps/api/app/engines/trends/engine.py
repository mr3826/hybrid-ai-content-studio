import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.trends.adapters.manual_signals import ManualSignalAdapter
from app.engines.trends.adapters.rss_signals import RssSignalAdapter
from app.engines.trends.contracts import (
    TopicSignal,
    TrendCluster,
    TrendEngineInput,
    TrendEngineResult,
)
from app.engines.trends.scoring import (
    build_trend_cluster,
    cluster_signals,
)
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.trend import TrendTopic


class TrendsEngine(BaseEngine):
    """Independent Trends Engine: Tracks topic momentum, velocity, recency decay,
    and source diversity within the niche without paid APIs, producing transparent,
    explainable scores.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)
        self._last_run_result: Optional[TrendEngineResult] = None
        self._history: Dict[str, EngineResult] = {}
        self._cached_clusters: Dict[str, TrendCluster] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("TrendsEngine rules cannot be empty.")
        if "weights" not in self.rules:
            raise ValueError("TrendsEngine rules missing 'weights' block.")
        if "thresholds" not in self.rules:
            raise ValueError("TrendsEngine rules missing 'thresholds' block.")
        if "baseline" not in self.rules:
            raise ValueError("TrendsEngine rules missing 'baseline' block.")

    def health(self) -> EngineHealth:
        try:
            self.validate_config()
            return EngineHealth(
                status="healthy",
                message="TrendsEngine is operational with valid scoring weights and thresholds.",
                details={
                    "weights": self.rules.get("weights", {}),
                    "thresholds": self.rules.get("thresholds", {}),
                    "rules_version": self.rules_version,
                },
            )
        except Exception as e:
            return EngineHealth(
                status="failing",
                message=f"TrendsEngine health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _gather_signals(
        self,
        engine_input: TrendEngineInput,
        session: Any = None,
    ) -> List[TopicSignal]:
        signals: List[TopicSignal] = []

        # 1. Custom / Manual signals passed directly
        if engine_input.custom_signals:
            signals.extend(engine_input.custom_signals)

        # 2. RSS Candidates Signals
        if engine_input.include_rss:
            adapter = RssSignalAdapter(session=session)
            rss_signals = await adapter.fetch_signals(window_hours=engine_input.time_window_hours)
            signals.extend(rss_signals)

        return signals

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        run_id = context.run_id or str(uuid.uuid4())

        engine_input = TrendEngineInput(**context.parameters) if context.parameters else TrendEngineInput()

        errors: List[str] = []
        clusters: List[TrendCluster] = []

        try:
            async with AsyncSessionLocal() as session:
                # Gather signals
                signals = await self._gather_signals(engine_input, session=session)

                # Cluster signals
                grouped = cluster_signals(
                    signals,
                    similarity_threshold=float(self.rules.get("clustering", {}).get("entity_overlap_threshold", 0.35)),
                )

                from app.repositories.trend_repository import TrendRepository
                repo = TrendRepository(session)

                # Build TrendClusters
                for group in grouped:
                    if len(group) < engine_input.min_mentions:
                        continue
                    cluster = build_trend_cluster(
                        signals=group,
                        rules=self.rules,
                        now=started_at,
                    )
                    # Upsert to database
                    await repo.upsert_cluster(cluster)
                    clusters.append(cluster)
                    self._cached_clusters[cluster.topic_key] = cluster

        except Exception as e:
            errors.append(f"TrendsEngine execution failed: {str(e)}")

        ended_at = datetime.now(timezone.utc)
        duration_ms = int((time.time() - start_time) * 1000)

        # Sort clusters descending by trend score
        clusters.sort(key=lambda c: c.trend_score, reverse=True)
        emerging = sum(1 for c in clusters if c.status == "emerging")
        suppressed = sum(1 for c in clusters if c.is_suppressed)

        explanations = [c.explanation.model_dump(mode="json") for c in clusters]

        engine_result = EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            rules_version=self.rules_version,
            run_id=run_id,
            success=len(errors) == 0,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            input_count=len(signals) if 'signals' in locals() else 0,
            output_count=len(clusters),
            rejected_count=suppressed,
            error_count=len(errors),
            summary=(
                f"Trends analysis processed {len(signals) if 'signals' in locals() else 0} signals into "
                f"{len(clusters)} topic clusters ({emerging} emerging, {suppressed} suppressed) in {duration_ms}ms"
            ),
            outputs=[c.model_dump(mode="json") for c in clusters],
            errors=errors,
            explanations=explanations,
        )

        self._history[run_id] = engine_result
        return engine_result

    async def dry_run(self, context: EngineContext) -> EngineResult:
        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        run_id = context.run_id or f"dry_run_{uuid.uuid4()}"

        engine_input = TrendEngineInput(**context.parameters) if context.parameters else TrendEngineInput()

        errors: List[str] = []
        clusters: List[TrendCluster] = []

        try:
            async with AsyncSessionLocal() as session:
                signals = await self._gather_signals(engine_input, session=session)

                grouped = cluster_signals(
                    signals,
                    similarity_threshold=float(self.rules.get("clustering", {}).get("entity_overlap_threshold", 0.35)),
                )

                for group in grouped:
                    if len(group) < engine_input.min_mentions:
                        continue
                    cluster = build_trend_cluster(
                        signals=group,
                        rules=self.rules,
                        now=started_at,
                    )
                    clusters.append(cluster)
                    self._cached_clusters[cluster.topic_key] = cluster

        except Exception as e:
            errors.append(f"TrendsEngine dry run failed: {str(e)}")

        ended_at = datetime.now(timezone.utc)
        duration_ms = int((time.time() - start_time) * 1000)

        clusters.sort(key=lambda c: c.trend_score, reverse=True)
        emerging = sum(1 for c in clusters if c.status == "emerging")
        suppressed = sum(1 for c in clusters if c.is_suppressed)
        explanations = [c.explanation.model_dump(mode="json") for c in clusters]

        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            rules_version=self.rules_version,
            run_id=run_id,
            success=len(errors) == 0,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            input_count=len(signals) if 'signals' in locals() else 0,
            output_count=len(clusters),
            rejected_count=suppressed,
            error_count=len(errors),
            summary=(
                f"[Dry Run] Trends analysis analyzed {len(signals) if 'signals' in locals() else 0} signals into "
                f"{len(clusters)} topic clusters without persisting changes."
            ),
            outputs=[c.model_dump(mode="json") for c in clusters],
            errors=errors,
            explanations=explanations,
        )

    def explain(self, result_id: str) -> EngineExplanation:
        """Provide detailed human-readable breakdown of an output decision for topic_key or run_id."""
        # 1. Check if cached by topic_key
        if result_id in self._cached_clusters:
            cl = self._cached_clusters[result_id]
            b = cl.explanation.breakdown
            factors = [
                {"name": "Mentions", "score": b.base_mentions_score, "text": cl.explanation.mentions_text},
                {"name": "Source Diversity", "score": b.source_diversity_score, "text": cl.explanation.sources_text},
                {"name": "Source Authority", "score": b.source_authority_score, "text": f"Avg trust {cl.source_authority_score:.0%}"},
                {"name": "Recency", "score": b.recency_score, "text": cl.explanation.recency_text},
                {"name": "Velocity & Baseline", "score": b.velocity_score, "text": f"{cl.explanation.velocity_text} ({cl.explanation.baseline_text})"},
                {"name": "Manual Boost", "value": b.manual_boost},
                {"name": "Suppressed", "value": b.is_suppressed},
            ]
            return EngineExplanation(
                result_id=result_id,
                summary=cl.explanation.summary,
                factors=factors,
            )

        # 2. Check history runs
        for run_res in self._history.values():
            for expl in run_res.explanations:
                if expl.get("topic_key") == result_id:
                    breakdown = expl.get("breakdown", {})
                    factors = [
                        {"name": "Mentions", "score": breakdown.get("base_mentions_score", 0)},
                        {"name": "Diversity", "score": breakdown.get("source_diversity_score", 0)},
                        {"name": "Authority", "score": breakdown.get("source_authority_score", 0)},
                        {"name": "Recency", "score": breakdown.get("recency_score", 0)},
                        {"name": "Velocity", "score": breakdown.get("velocity_score", 0)},
                    ]
                    return EngineExplanation(
                        result_id=result_id,
                        summary=expl.get("summary", "Trend Topic Explanation"),
                        factors=factors,
                    )

        return EngineExplanation(
            result_id=result_id,
            summary=f"No cached explanation found for result ID {result_id}",
            factors=[],
        )
