from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engines.trends.contracts import TrendCluster
from app.models.trend import TrendHistory, TrendTopic
from app.repositories.base import BaseRepository


class TrendRepository(BaseRepository[TrendTopic]):
    """Storage boundary for trend topics, momentum clusters, and historical snapshots."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, topic_id: str) -> Optional[TrendTopic]:
        stmt = (
            select(TrendTopic)
            .options(selectinload(TrendTopic.history))
            .where(TrendTopic.id == topic_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_key(self, topic_key: str) -> Optional[TrendTopic]:
        stmt = (
            select(TrendTopic)
            .options(selectinload(TrendTopic.history))
            .where(TrendTopic.topic_key == topic_key)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_topics(
        self,
        status: Optional[str] = None,
        pillar: Optional[str] = None,
        min_score: Optional[float] = None,
        is_suppressed: Optional[bool] = None,
        sort_by: str = "trend_score",  # "trend_score", "velocity", "recency", "mentions"
        limit: int = 50,
    ) -> List[TrendTopic]:
        stmt = select(TrendTopic).options(selectinload(TrendTopic.history))

        if status:
            stmt = stmt.where(TrendTopic.status == status)
        if pillar:
            stmt = stmt.where(TrendTopic.pillar == pillar)
        if min_score is not None:
            stmt = stmt.where(TrendTopic.trend_score >= min_score)
        if is_suppressed is not None:
            stmt = stmt.where(TrendTopic.is_suppressed == is_suppressed)

        if sort_by == "velocity":
            stmt = stmt.order_by(TrendTopic.velocity.desc(), TrendTopic.trend_score.desc())
        elif sort_by == "recency":
            stmt = stmt.order_by(TrendTopic.first_seen_at.desc())
        elif sort_by == "mentions":
            stmt = stmt.order_by(TrendTopic.mention_count.desc())
        else:
            stmt = stmt.order_by(TrendTopic.trend_score.desc(), TrendTopic.first_seen_at.desc())

        stmt = stmt.limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def upsert_cluster(self, cluster: TrendCluster) -> TrendTopic:
        """Upsert a TrendCluster into the database, preserving user overrides (boost/suppress)."""
        existing = await self.get_by_key(cluster.topic_key)

        signal_ids = [s.signal_id for s in cluster.signals]
        source_breakdown = [
            {
                "source_name": s.source_name,
                "source_type": s.source_type,
                "trust_weight": s.trust_weight,
                "url": s.url,
            }
            for s in cluster.signals
        ]
        explanation_dict = cluster.explanation.model_dump(mode="json")

        if existing:
            # Preserve user overrides if already set
            manual_boost = existing.manual_boost
            is_suppressed = existing.is_suppressed
            historical_baseline = existing.historical_baseline

            existing.title = cluster.title
            existing.summary = cluster.summary
            existing.pillar = cluster.pillar
            existing.keywords = cluster.keywords
            existing.trend_score = 0.0 if is_suppressed else cluster.trend_score
            existing.momentum_score = cluster.momentum_score
            existing.mention_count = cluster.mention_count
            existing.distinct_sources_count = cluster.distinct_sources_count
            existing.source_diversity_score = cluster.source_diversity_score
            existing.source_authority_score = cluster.source_authority_score
            existing.velocity = cluster.velocity
            existing.velocity_ratio = cluster.velocity_ratio
            existing.historical_baseline = historical_baseline
            existing.last_seen_at = cluster.last_seen_at
            existing.status = "archived" if is_suppressed else cluster.status
            existing.signal_ids = signal_ids
            existing.source_breakdown = source_breakdown
            existing.explanation = explanation_dict

            topic = existing
        else:
            topic = TrendTopic(
                topic_key=cluster.topic_key,
                title=cluster.title,
                summary=cluster.summary,
                pillar=cluster.pillar,
                keywords=cluster.keywords,
                trend_score=cluster.trend_score,
                momentum_score=cluster.momentum_score,
                mention_count=cluster.mention_count,
                distinct_sources_count=cluster.distinct_sources_count,
                source_diversity_score=cluster.source_diversity_score,
                source_authority_score=cluster.source_authority_score,
                velocity=cluster.velocity,
                velocity_ratio=cluster.velocity_ratio,
                historical_baseline=1.0,
                first_seen_at=cluster.first_seen_at,
                last_seen_at=cluster.last_seen_at,
                manual_boost=cluster.manual_boost,
                is_suppressed=cluster.is_suppressed,
                status=cluster.status,
                signal_ids=signal_ids,
                source_breakdown=source_breakdown,
                explanation=explanation_dict,
            )
            self.session.add(topic)

        await self.session.commit()
        await self.session.refresh(topic)

        # Record historical snapshot
        history_entry = TrendHistory(
            topic_id=topic.id,
            recorded_at=datetime.now(timezone.utc),
            trend_score=topic.trend_score,
            momentum_score=topic.momentum_score,
            mention_count=topic.mention_count,
            velocity=topic.velocity,
            snapshot_data={
                "velocity_ratio": topic.velocity_ratio,
                "status": topic.status,
                "distinct_sources": topic.distinct_sources_count,
            },
        )
        self.session.add(history_entry)
        await self.session.commit()

        return topic

    async def apply_boost(self, topic_id: str, boost_factor: float) -> Optional[TrendTopic]:
        topic = await self.get_by_id(topic_id)
        if not topic:
            return None
        topic.manual_boost = max(0.1, min(5.0, boost_factor))
        # Recalculate trend score
        if not topic.is_suppressed:
            raw = topic.explanation.get("breakdown", {}).get("raw_score", topic.trend_score)
            topic.trend_score = min(100.0, max(0.0, raw * topic.manual_boost))
            if "breakdown" in topic.explanation:
                topic.explanation["breakdown"]["manual_boost"] = topic.manual_boost
                topic.explanation["breakdown"]["final_score"] = topic.trend_score

        await self.session.commit()
        await self.session.refresh(topic)
        return topic

    async def toggle_suppress(self, topic_id: str, suppress: bool) -> Optional[TrendTopic]:
        topic = await self.get_by_id(topic_id)
        if not topic:
            return None
        topic.is_suppressed = suppress
        if suppress:
            topic.trend_score = 0.0
            topic.status = "archived"
        else:
            raw = topic.explanation.get("breakdown", {}).get("raw_score", 50.0)
            topic.trend_score = min(100.0, max(0.0, raw * topic.manual_boost))
            topic.status = "active"

        if "breakdown" in topic.explanation:
            topic.explanation["breakdown"]["is_suppressed"] = suppress
            topic.explanation["breakdown"]["final_score"] = topic.trend_score

        await self.session.commit()
        await self.session.refresh(topic)
        return topic

    async def get_history(self, topic_id: str, limit: int = 30) -> List[TrendHistory]:
        stmt = (
            select(TrendHistory)
            .where(TrendHistory.topic_id == topic_id)
            .order_by(TrendHistory.recorded_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
