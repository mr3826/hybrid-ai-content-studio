from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rss import DiscoveredCandidate
from app.repositories.base import BaseRepository


class OpportunityRepository(BaseRepository[DiscoveredCandidate]):
    """Storage boundary for discovered signals and candidate opportunities awaiting human gate approval."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, opportunity_id: str) -> Optional[DiscoveredCandidate]:
        stmt = select(DiscoveredCandidate).where(DiscoveredCandidate.id == opportunity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_opportunities(
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

    async def get_opportunity(self, opportunity_id: str) -> Optional[DiscoveredCandidate]:
        return await self.get_by_id(opportunity_id)

    async def record_opportunity(self, data: Dict[str, Any]) -> DiscoveredCandidate:
        candidate = DiscoveredCandidate(**data)
        self.session.add(candidate)
        await self.session.commit()
        await self.session.refresh(candidate)
        return candidate

    async def update_status(self, opportunity_id: str, status: str) -> bool:
        candidate = await self.get_by_id(opportunity_id)
        if not candidate:
            return False
        candidate.status = status
        await self.session.commit()
        return True
