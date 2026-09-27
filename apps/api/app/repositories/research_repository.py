import copy
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.opportunity import Opportunity
from app.models.research import ResearchPacket, ResearchRevision
from app.repositories.base import BaseRepository


class ResearchRepository(BaseRepository[ResearchPacket]):
    """Storage boundary for traceable research packets, claim verification audit, and revisions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, packet_id: str) -> Optional[ResearchPacket]:
        stmt = (
            select(ResearchPacket)
            .where(ResearchPacket.id == packet_id)
            .options(selectinload(ResearchPacket.revisions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_opportunity_id(self, opportunity_id: str) -> Optional[ResearchPacket]:
        stmt = (
            select(ResearchPacket)
            .where(ResearchPacket.opportunity_id == opportunity_id)
            .options(selectinload(ResearchPacket.revisions))
            .order_by(desc(ResearchPacket.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> Optional[ResearchPacket]:
        stmt = (
            select(ResearchPacket)
            .where(ResearchPacket.slug == slug)
            .options(selectinload(ResearchPacket.revisions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_packets(
        self,
        opportunity_id: Optional[str] = None,
        is_verified: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> List[ResearchPacket]:
        stmt = select(ResearchPacket).options(selectinload(ResearchPacket.revisions))

        if opportunity_id:
            stmt = stmt.where(ResearchPacket.opportunity_id == opportunity_id)
        if is_verified is not None:
            stmt = stmt.where(ResearchPacket.is_verified == is_verified)
        if search:
            stmt = stmt.where(ResearchPacket.topic.ilike(f"%{search}%"))

        stmt = stmt.order_by(desc(ResearchPacket.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _packet_to_snapshot(self, packet: ResearchPacket) -> Dict[str, Any]:
        """Serialize packet into full revision snapshot."""
        return {
            "id": packet.id,
            "opportunity_id": packet.opportunity_id,
            "topic": packet.topic,
            "slug": packet.slug,
            "summary": packet.summary,
            "primary_sources": copy.deepcopy(packet.primary_sources or []),
            "supporting_sources": copy.deepcopy(packet.supporting_sources or []),
            "facts": copy.deepcopy(packet.facts or []),
            "numbers": copy.deepcopy(packet.numbers or []),
            "dates": copy.deepcopy(packet.dates or []),
            "entities": copy.deepcopy(packet.entities or []),
            "claims": copy.deepcopy(packet.claims or []),
            "contradictions": copy.deepcopy(packet.contradictions or []),
            "uncertain_claims": copy.deepcopy(packet.uncertain_claims or []),
            "things_not_to_claim": copy.deepcopy(packet.things_not_to_claim or []),
            "version": packet.version,
            "is_verified": packet.is_verified,
            "verified_at": packet.verified_at.isoformat() if packet.verified_at else None,
            "verified_by": packet.verified_by,
        }

    async def create_packet(self, packet_data: Dict[str, Any]) -> ResearchPacket:
        """Create new research packet and record its baseline revision 1."""
        packet_id = packet_data.get("id") or str(uuid.uuid4())
        topic = packet_data.get("topic", "Research Topic")
        slug = packet_data.get("slug") or f"{re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')[:180]}-{packet_id[:8]}"

        # Helper to convert Pydantic models or dicts to json-compatible dicts
        def _clean_list(items: Any) -> List[Dict[str, Any]]:
            if not items:
                return []
            res = []
            for item in items:
                if hasattr(item, "model_dump"):
                    res.append(item.model_dump())
                elif isinstance(item, dict):
                    res.append(item)
            return res

        primary_sources = _clean_list(packet_data.get("primary_sources"))
        supporting_sources = _clean_list(packet_data.get("supporting_sources"))
        facts = _clean_list(packet_data.get("facts"))
        numbers = _clean_list(packet_data.get("numbers"))
        dates = _clean_list(packet_data.get("dates"))
        entities = _clean_list(packet_data.get("entities"))
        claims = _clean_list(packet_data.get("claims"))
        contradictions = _clean_list(packet_data.get("contradictions"))
        uncertain_claims = _clean_list(packet_data.get("uncertain_claims"))
        things_not_to_claim = _clean_list(packet_data.get("things_not_to_claim"))

        packet = ResearchPacket(
            id=packet_id,
            opportunity_id=packet_data.get("opportunity_id"),
            topic=topic,
            slug=slug,
            summary=packet_data.get("summary", ""),
            primary_sources=primary_sources,
            supporting_sources=supporting_sources,
            facts=facts,
            numbers=numbers,
            dates=dates,
            entities=entities,
            claims=claims,
            contradictions=contradictions,
            uncertain_claims=uncertain_claims,
            things_not_to_claim=things_not_to_claim,
            version=1,
            is_verified=packet_data.get("is_verified", False),
            verified_at=packet_data.get("verified_at"),
            verified_by=packet_data.get("verified_by"),
        )
        self.session.add(packet)
        await self.session.flush()

        # Initial revision
        initial_revision = ResearchRevision(
            id=str(uuid.uuid4()),
            packet_id=packet.id,
            revision_number=1,
            changed_by="engine",
            change_summary="Initial automated research extraction",
            snapshot=self._packet_to_snapshot(packet),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(initial_revision)
        await self.session.flush()

        return packet

    async def update_packet(
        self,
        packet: ResearchPacket,
        updates: Dict[str, Any],
        changed_by: str = "creator",
        change_summary: str = "Manual edit by creator",
    ) -> ResearchPacket:
        """Update research packet and archive new state into research_revisions."""
        # Apply updates
        if "summary" in updates and updates["summary"] is not None:
            packet.summary = updates["summary"]
        if "primary_sources" in updates and updates["primary_sources"] is not None:
            packet.primary_sources = updates["primary_sources"]
        if "supporting_sources" in updates and updates["supporting_sources"] is not None:
            packet.supporting_sources = updates["supporting_sources"]
        if "facts" in updates and updates["facts"] is not None:
            packet.facts = updates["facts"]
        if "numbers" in updates and updates["numbers"] is not None:
            packet.numbers = updates["numbers"]
        if "dates" in updates and updates["dates"] is not None:
            packet.dates = updates["dates"]
        if "entities" in updates and updates["entities"] is not None:
            packet.entities = updates["entities"]
        if "claims" in updates and updates["claims"] is not None:
            # Enforce that claims are normalized and labeled
            normalized_claims = []
            for c in updates["claims"]:
                claim_dict = c if isinstance(c, dict) else c.model_dump()
                if "verification_status" not in claim_dict or not claim_dict["verification_status"]:
                    claim_dict["verification_status"] = "manually_entered"
                normalized_claims.append(claim_dict)
            packet.claims = normalized_claims
        if "contradictions" in updates and updates["contradictions"] is not None:
            packet.contradictions = updates["contradictions"]
        if "uncertain_claims" in updates and updates["uncertain_claims"] is not None:
            packet.uncertain_claims = updates["uncertain_claims"]
        if "things_not_to_claim" in updates and updates["things_not_to_claim"] is not None:
            packet.things_not_to_claim = updates["things_not_to_claim"]

        # Increment version
        packet.version += 1

        # Record new revision state
        new_revision = ResearchRevision(
            id=str(uuid.uuid4()),
            packet_id=packet.id,
            revision_number=packet.version,
            changed_by=changed_by,
            change_summary=change_summary,
            snapshot=self._packet_to_snapshot(packet),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(new_revision)
        await self.session.flush()
        return packet

    async def verify_packet(
        self,
        packet_id: str,
        verified_by: str = "creator",
    ) -> Optional[ResearchPacket]:
        """Mark research packet verified by human and update linked opportunity workflow."""
        packet = await self.get_by_id(packet_id)
        if not packet:
            return None

        packet.is_verified = True
        packet.verified_at = datetime.now(timezone.utc)
        packet.verified_by = verified_by

        # If linked to an Opportunity, progress it to in_production
        if packet.opportunity_id:
            opp_stmt = select(Opportunity).where(Opportunity.id == packet.opportunity_id)
            opp = (await self.session.execute(opp_stmt)).scalar_one_or_none()
            if opp and opp.status in ("research_ready", "approved", "needs_review"):
                opp.status = "in_production"

        await self.session.flush()
        return packet

    async def get_revisions(self, packet_id: str) -> List[ResearchRevision]:
        """Fetch all revisions for a research packet in descending order."""
        stmt = (
            select(ResearchRevision)
            .where(ResearchRevision.packet_id == packet_id)
            .order_by(desc(ResearchRevision.revision_number))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revert_to_revision(
        self,
        packet_id: str,
        revision_number: int,
    ) -> Optional[ResearchPacket]:
        """Revert packet contents to an earlier revision snapshot while recording audit trail."""
        packet = await self.get_by_id(packet_id)
        if not packet:
            return None

        rev_stmt = select(ResearchRevision).where(
            ResearchRevision.packet_id == packet_id,
            ResearchRevision.revision_number == revision_number,
        )
        rev = (await self.session.execute(rev_stmt)).scalar_one_or_none()
        if not rev:
            return None

        # Restore from snapshot
        snap = rev.snapshot
        packet.summary = snap.get("summary", packet.summary)
        packet.primary_sources = snap.get("primary_sources", packet.primary_sources)
        packet.supporting_sources = snap.get("supporting_sources", packet.supporting_sources)
        packet.facts = snap.get("facts", packet.facts)
        packet.numbers = snap.get("numbers", packet.numbers)
        packet.dates = snap.get("dates", packet.dates)
        packet.entities = snap.get("entities", packet.entities)
        packet.claims = snap.get("claims", packet.claims)
        packet.contradictions = snap.get("contradictions", packet.contradictions)
        packet.uncertain_claims = snap.get("uncertain_claims", packet.uncertain_claims)
        packet.things_not_to_claim = snap.get("things_not_to_claim", packet.things_not_to_claim)

        # Increment version
        packet.version += 1

        # Record new reverted revision
        reverted_revision = ResearchRevision(
            id=str(uuid.uuid4()),
            packet_id=packet.id,
            revision_number=packet.version,
            changed_by="creator",
            change_summary=f"Reverted to revision #{revision_number}",
            snapshot=self._packet_to_snapshot(packet),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(reverted_revision)

        await self.session.flush()
        return packet
