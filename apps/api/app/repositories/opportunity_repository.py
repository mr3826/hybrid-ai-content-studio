from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.opportunity.contracts import OpportunityItem
from app.models.opportunity import Opportunity
from app.models.rss import DiscoveredCandidate
from app.repositories.base import BaseRepository


class OpportunityRepository(BaseRepository[Opportunity]):
    """Storage boundary for evaluated content opportunities and Creator Cockpit workflow gates."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, opportunity_id: str) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.id == opportunity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_opportunities(
        self,
        status: Optional[str] = None,
        pillar: Optional[str] = None,
        min_score: Optional[float] = None,
        content_family: Optional[str] = None,
        sort_by: str = "opportunity_score",
        limit: int = 50,
    ) -> List[Opportunity]:
        stmt = select(Opportunity)

        if status:
            stmt = stmt.where(Opportunity.status == status)
        if pillar:
            stmt = stmt.where(Opportunity.pillar == pillar)
        if min_score is not None:
            stmt = stmt.where(Opportunity.opportunity_score >= min_score)
        if content_family:
            stmt = stmt.where(Opportunity.suggested_content_family == content_family)

        if sort_by == "trend_score":
            stmt = stmt.order_by(Opportunity.trend_score.desc(), Opportunity.opportunity_score.desc())
        elif sort_by == "recency":
            stmt = stmt.order_by(Opportunity.created_at.desc())
        elif sort_by == "originality":
            stmt = stmt.order_by(Opportunity.originality_potential.desc(), Opportunity.opportunity_score.desc())
        else:
            stmt = stmt.order_by(Opportunity.opportunity_score.desc(), Opportunity.created_at.desc())

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_opportunity(self, item: OpportunityItem) -> Opportunity:
        """Upsert opportunity by slug, preserving human review decisions if already made."""
        existing = await self.get_by_slug(item.slug)

        breakdown_dict = item.score_breakdown.model_dump(mode="json")

        if existing:
            # If item was already human-reviewed (e.g. approved, rejected, watching), keep human status
            if existing.status in ("approved", "research_ready", "in_production", "ready_to_publish", "published"):
                status_to_keep = existing.status
            elif existing.status in ("watching", "rejected"):
                status_to_keep = existing.status
            else:
                status_to_keep = item.status

            existing.topic = item.topic
            existing.pillar = item.pillar
            existing.candidate_id = item.candidate_id or existing.candidate_id
            existing.trend_id = item.trend_id or existing.trend_id
            existing.status = status_to_keep
            existing.opportunity_score = item.opportunity_score
            existing.trend_score = item.trend_score
            existing.niche_fit_score = item.score_breakdown.niche_fit
            existing.originality_potential = item.originality_potential
            existing.audience_usefulness = item.score_breakdown.audience_usefulness
            existing.evergreen_value = item.evergreen_value
            existing.commercial_fit = item.commercial_fit
            existing.content_family_potential = item.score_breakdown.content_family_potential
            existing.sponsor_relevance = item.score_breakdown.sponsor_relevance
            existing.saturation_penalty = item.score_breakdown.saturation_penalty
            existing.production_effort = item.production_effort
            existing.estimated_cost = item.estimated_cost
            existing.estimated_time_minutes = item.estimated_time_minutes
            existing.suggested_original_angle = item.suggested_original_angle
            existing.suggested_content_family = item.suggested_content_family
            existing.risks = item.risks
            existing.why = item.why
            existing.recommended_action = item.recommended_action
            existing.score_breakdown = breakdown_dict
            if item.source_references:
                existing.source_references = item.source_references

            opp = existing
        else:
            opp = Opportunity(
                topic=item.topic,
                slug=item.slug,
                candidate_id=item.candidate_id,
                trend_id=item.trend_id,
                pillar=item.pillar,
                status=item.status,
                opportunity_score=item.opportunity_score,
                trend_score=item.trend_score,
                niche_fit_score=item.score_breakdown.niche_fit,
                originality_potential=item.originality_potential,
                audience_usefulness=item.score_breakdown.audience_usefulness,
                evergreen_value=item.evergreen_value,
                commercial_fit=item.commercial_fit,
                content_family_potential=item.score_breakdown.content_family_potential,
                sponsor_relevance=item.score_breakdown.sponsor_relevance,
                saturation_penalty=item.score_breakdown.saturation_penalty,
                production_effort=item.production_effort,
                estimated_cost=item.estimated_cost,
                estimated_time_minutes=item.estimated_time_minutes,
                suggested_original_angle=item.suggested_original_angle,
                suggested_content_family=item.suggested_content_family,
                risks=item.risks,
                why=item.why,
                recommended_action=item.recommended_action,
                score_breakdown=breakdown_dict,
                source_references=item.source_references,
            )
            self.session.add(opp)

        await self.session.commit()
        await self.session.refresh(opp)
        return opp

    async def update_status(
        self,
        opportunity_id: str,
        status: str,
        rejection_reason: Optional[str] = None,
    ) -> Optional[Opportunity]:
        """Apply human gate decision: approve -> research_ready, watch, or reject."""
        opp = await self.get_by_id(opportunity_id)
        if not opp:
            return None

        opp.status = status
        opp.reviewed_at = datetime.now(timezone.utc)
        if rejection_reason is not None:
            opp.rejection_reason = rejection_reason

        await self.session.commit()
        await self.session.refresh(opp)
        return opp

    async def get_top_opportunities(self, limit: int = 5) -> List[Opportunity]:
        """Fetch highest scoring opportunities that need human review decision."""
        stmt = (
            select(Opportunity)
            .where(Opportunity.status.in_(["needs_review", "watching"]))
            .order_by(Opportunity.opportunity_score.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_cockpit_counts(self) -> Dict[str, int]:
        """Aggregate decision counts across studio lifecycle."""
        # 1. Signals Today (discovered candidates within last 24h)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        cand_stmt = select(func.count(DiscoveredCandidate.id)).where(
            DiscoveredCandidate.first_seen_at >= today_start
        )
        cand_res = await self.session.execute(cand_stmt)
        signals_today = cand_res.scalar_one() or 0

        # 2. Opportunity workflow status counts
        opp_stmt = select(Opportunity.status, func.count(Opportunity.id)).group_by(Opportunity.status)
        opp_res = await self.session.execute(opp_stmt)
        status_map = dict(opp_res.all())

        return {
            "signals_today": signals_today,
            "needs_review": status_map.get("needs_review", 0),
            "watching": status_map.get("watching", 0),
            "research_ready": status_map.get("research_ready", 0) + status_map.get("approved", 0),
            "in_production": status_map.get("in_production", 0),
            "ready_to_publish": status_map.get("ready_to_publish", 0),
            "published": status_map.get("published", 0),
        }

    # ---------------------------------------------------------
    # Discovered Candidate Queries (Phase 4 RSS Engine support)
    # ---------------------------------------------------------
    async def list_candidates(
        self,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        pillar: Optional[str] = None,
        in_niche_only: bool = False,
        limit: int = 50,
    ) -> List[DiscoveredCandidate]:
        stmt = select(DiscoveredCandidate).order_by(
            DiscoveredCandidate.authority_score.desc(),
            DiscoveredCandidate.published_at.desc(),
        )
        if status:
            stmt = stmt.where(DiscoveredCandidate.status == status)
        if pillar:
            stmt = stmt.where(DiscoveredCandidate.pillar == pillar)
        if in_niche_only:
            stmt = stmt.where(DiscoveredCandidate.is_in_niche.is_(True))
        if source_type:
            stmt = stmt.where(DiscoveredCandidate.primary_source == source_type)

        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_candidate(self, candidate_id: str) -> Optional[DiscoveredCandidate]:
        stmt = select(DiscoveredCandidate).where(DiscoveredCandidate.id == candidate_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_opportunity(self, candidate_id: str) -> Optional[DiscoveredCandidate]:
        return await self.get_candidate(candidate_id)

    async def record_opportunity(self, data: Dict[str, Any]) -> DiscoveredCandidate:
        candidate = DiscoveredCandidate(**data)
        self.session.add(candidate)
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate
