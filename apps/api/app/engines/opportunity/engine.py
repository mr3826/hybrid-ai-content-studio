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
from app.engines.core.registry import engine_registry
from app.engines.opportunity.contracts import (
    OpportunityEngineInput,
    OpportunityEngineResult,
    OpportunityItem,
)
from app.engines.opportunity.evaluator import build_opportunity_item
from app.models.brand import BrandMemoryItem, BrandProfile, SINGLETON_BRAND_ID
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.opportunity import Opportunity
from app.models.rss import DiscoveredCandidate
from app.models.trend import TrendTopic


class OpportunityEngine(BaseEngine):
    """Opportunity Intelligence Engine: Computes 10-factor opportunity potential,
    original test angles, and content families determining if a topic is worth creating
    for this specific channel.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)
        self._history: Dict[str, EngineResult] = {}
        self._cached_opportunities: Dict[str, OpportunityItem] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("OpportunityEngine rules cannot be empty.")
        if "weights" not in self.rules:
            raise ValueError("OpportunityEngine rules missing 'weights' block.")
        if "penalties" not in self.rules:
            raise ValueError("OpportunityEngine rules missing 'penalties' block.")

    def health(self) -> EngineHealth:
        try:
            self.validate_config()
            return EngineHealth(
                status="healthy",
                message="OpportunityEngine is operational with 10-dimension scoring weights.",
                details={
                    "weights": self.rules.get("weights", {}),
                    "penalties": self.rules.get("penalties", {}),
                    "rules_version": self.rules_version,
                },
            )
        except Exception as e:
            return EngineHealth(
                status="failing",
                message=f"OpportunityEngine health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _evaluate_topics(
        self,
        engine_input: OpportunityEngineInput,
        session: Any,
        dry_run: bool = False,
    ) -> List[OpportunityItem]:
        # 1. Fetch active Niche and Brand Profiles
        niche_stmt = select(NicheProfile).where(NicheProfile.id == SINGLETON_NICHE_ID)
        niche = (await session.execute(niche_stmt)).scalar_one_or_none()

        brand_stmt = select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID)
        brand = (await session.execute(brand_stmt)).scalar_one_or_none()

        memory_stmt = select(BrandMemoryItem).order_by(BrandMemoryItem.created_at.desc()).limit(100)
        brand_memory = list((await session.execute(memory_stmt)).scalars().all())

        raw_items: List[Dict[str, Any]] = []

        # 2. Custom Topics
        if engine_input.custom_topics:
            for ct in engine_input.custom_topics:
                raw_items.append({
                    "topic": ct.get("topic") or ct.get("title", "Custom Topic"),
                    "summary": ct.get("summary", ""),
                    "pillar": ct.get("pillar"),
                    "trend_score": float(ct.get("trend_score", 50.0)),
                    "candidate_id": ct.get("candidate_id"),
                    "trend_id": ct.get("trend_id"),
                    "sources": ct.get("sources", []),
                })

        # 3. Discovered in-niche candidates from RSS
        if engine_input.include_candidates:
            cand_stmt = (
                select(DiscoveredCandidate)
                .where(DiscoveredCandidate.is_in_niche.is_(True))
                .order_by(DiscoveredCandidate.published_at.desc())
                .limit(engine_input.limit)
            )
            candidates = list((await session.execute(cand_stmt)).scalars().all())
            for c in candidates:
                raw_items.append({
                    "topic": c.title,
                    "summary": c.summary,
                    "pillar": c.pillar,
                    "trend_score": 60.0,  # candidate baseline
                    "candidate_id": c.id,
                    "trend_id": None,
                    "sources": c.sources or [{"feed_name": c.primary_source, "url": c.canonical_url}],
                })

        # 4. Trend Topics from Trends Engine
        if engine_input.include_trends:
            trend_stmt = (
                select(TrendTopic)
                .where(TrendTopic.is_suppressed.is_(False))
                .order_by(TrendTopic.trend_score.desc())
                .limit(engine_input.limit)
            )
            trends = list((await session.execute(trend_stmt)).scalars().all())
            for t in trends:
                raw_items.append({
                    "topic": t.title,
                    "summary": t.summary,
                    "pillar": t.pillar,
                    "trend_score": t.trend_score,
                    "candidate_id": None,
                    "trend_id": t.id,
                    "sources": t.source_breakdown,
                })

        scored_items: List[OpportunityItem] = []
        seen_slugs: set = set()
        from app.repositories.opportunity_repository import OpportunityRepository
        repo = OpportunityRepository(session)

        for item in raw_items:
            opp_item = build_opportunity_item(
                topic=item["topic"],
                summary=item["summary"],
                pillar=item["pillar"],
                trend_score=item["trend_score"],
                candidate_id=item["candidate_id"],
                trend_id=item["trend_id"],
                niche=niche,
                brand=brand,
                brand_memory=brand_memory,
                rules=self.rules,
                sources=item["sources"],
            )

            if opp_item.slug in seen_slugs:
                continue
            seen_slugs.add(opp_item.slug)

            if opp_item.opportunity_score < engine_input.min_score:
                continue

            self._cached_opportunities[opp_item.slug] = opp_item

            if not dry_run:
                saved = await repo.upsert_opportunity(opp_item)
                opp_item.id = saved.id
                opp_item.status = saved.status

            scored_items.append(opp_item)

        # Sort descending by opportunity score
        scored_items.sort(key=lambda o: o.opportunity_score, reverse=True)
        return scored_items

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        run_id = context.run_id or str(uuid.uuid4())

        engine_input = OpportunityEngineInput(**context.parameters) if context.parameters else OpportunityEngineInput()
        errors: List[str] = []
        opportunities: List[OpportunityItem] = []

        try:
            async with AsyncSessionLocal() as session:
                opportunities = await self._evaluate_topics(engine_input, session=session, dry_run=False)
        except Exception as e:
            errors.append(f"OpportunityEngine execution failed: {str(e)}")

        ended_at = datetime.now(timezone.utc)
        duration_ms = int((time.time() - start_time) * 1000)

        high_priority = sum(1 for o in opportunities if o.opportunity_score >= 70.0)

        explanations = [
            {
                "topic": o.topic,
                "slug": o.slug,
                "score": o.opportunity_score,
                "why": o.why,
                "action": o.recommended_action,
                "breakdown": o.score_breakdown.model_dump(mode="json"),
            }
            for o in opportunities
        ]

        engine_result = EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            rules_version=self.rules_version,
            run_id=run_id,
            success=len(errors) == 0,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            input_count=len(opportunities),
            output_count=len(opportunities),
            rejected_count=0,
            error_count=len(errors),
            summary=(
                f"Opportunity Intelligence scored {len(opportunities)} candidate topics "
                f"({high_priority} high priority) in {duration_ms}ms"
            ),
            outputs=[o.model_dump(mode="json") for o in opportunities],
            errors=errors,
            explanations=explanations,
        )

        self._history[run_id] = engine_result
        return engine_result

    async def dry_run(self, context: EngineContext) -> EngineResult:
        start_time = time.time()
        started_at = datetime.now(timezone.utc)
        run_id = context.run_id or f"dry_run_{uuid.uuid4()}"

        engine_input = OpportunityEngineInput(**context.parameters) if context.parameters else OpportunityEngineInput()
        errors: List[str] = []
        opportunities: List[OpportunityItem] = []

        try:
            async with AsyncSessionLocal() as session:
                opportunities = await self._evaluate_topics(engine_input, session=session, dry_run=True)
        except Exception as e:
            errors.append(f"OpportunityEngine dry run failed: {str(e)}")

        ended_at = datetime.now(timezone.utc)
        duration_ms = int((time.time() - start_time) * 1000)

        explanations = [
            {
                "topic": o.topic,
                "slug": o.slug,
                "score": o.opportunity_score,
                "why": o.why,
                "breakdown": o.score_breakdown.model_dump(mode="json"),
            }
            for o in opportunities
        ]

        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            rules_version=self.rules_version,
            run_id=run_id,
            success=len(errors) == 0,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            input_count=len(opportunities),
            output_count=len(opportunities),
            rejected_count=0,
            error_count=len(errors),
            summary=f"[Dry Run] Evaluated {len(opportunities)} opportunities without persisting changes.",
            outputs=[o.model_dump(mode="json") for o in opportunities],
            errors=errors,
            explanations=explanations,
        )

    def explain(self, result_id: str) -> EngineExplanation:
        """Provide detailed human-readable breakdown of an opportunity decision."""
        if result_id in self._cached_opportunities:
            opp = self._cached_opportunities[result_id]
            b = opp.score_breakdown
            factors = [
                {"name": "Niche Fit", "score": b.niche_fit, "weight": 18, "max": 18},
                {"name": "Original Test Potential", "score": b.original_value, "weight": 20, "max": 20},
                {"name": "Audience Usefulness", "score": b.audience_usefulness, "weight": 15, "max": 15},
                {"name": "Search / Evergreen Value", "score": b.evergreen_value, "weight": 12, "max": 12},
                {"name": "Trend Momentum", "score": b.trend_momentum, "weight": 10, "max": 10},
                {"name": "Commercial Fit", "score": b.commercial_fit, "weight": 10, "max": 10},
                {"name": "Content-Family Potential", "score": b.content_family_potential, "weight": 5, "max": 5},
                {"name": "Sponsor Relevance", "score": b.sponsor_relevance, "weight": 3, "max": 3},
                {"name": "Production Economy", "score": b.production_effort_score, "weight": 4, "max": 4},
                {"name": "Channel Saturation Penalty", "score": -b.saturation_penalty, "penalty": True},
            ]
            return EngineExplanation(
                result_id=result_id,
                summary=f"Opportunity Score: {opp.opportunity_score:.1f}/100. {opp.why}",
                factors=factors,
            )

        return EngineExplanation(
            result_id=result_id,
            summary=f"No cached explanation found for {result_id}",
            factors=[],
        )
