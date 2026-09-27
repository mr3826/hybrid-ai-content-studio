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
from app.engines.research.contracts import (
    ResearchEngineInput,
    ResearchEngineResult,
    ResearchPacketItem,
)
from app.engines.research.extractor import extract_research_packet
from app.models.opportunity import Opportunity
from app.models.research import ResearchPacket, ResearchRevision


class ResearchEngine(BaseEngine):
    """Evidence-Based Research Engine: Extracts verifiable facts, numbers, dates,
    and claims from source articles and opportunities, enforcing strict claim
    verification status (source-backed, explicitly_uncertain, manually_entered)
    and revision tracking.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)
        self._history: Dict[str, EngineResult] = {}
        self._last_packets: Dict[str, ResearchPacketItem] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("ResearchEngine rules cannot be empty.")
        if "uncertainty_keywords" not in self.rules:
            raise ValueError("ResearchEngine rules missing 'uncertainty_keywords'.")
        if "hype_patterns" not in self.rules:
            raise ValueError("ResearchEngine rules missing 'hype_patterns'.")

    def health(self) -> EngineHealth:
        try:
            self.validate_config()
            return EngineHealth(
                status="healthy",
                message="ResearchEngine is operational with evidence extraction & skepticism rules.",
                details={
                    "rules_version": self.rules_version,
                    "uncertainty_keywords_count": len(self.rules.get("uncertainty_keywords", [])),
                    "hype_patterns_count": len(self.rules.get("hype_patterns", [])),
                },
            )
        except Exception as e:
            return EngineHealth(
                status="failing",
                message=f"ResearchEngine health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def generate_packet(
        self,
        engine_input: ResearchEngineInput,
        session: Any,
        dry_run: bool = False,
    ) -> ResearchPacketItem:
        """Construct research packet from opportunity or direct inputs and persist to storage."""
        topic = engine_input.topic
        sources: List[Dict[str, Any]] = list(engine_input.raw_sources or [])
        opp_id = engine_input.opportunity_id

        # If opportunity_id provided, load opportunity details and source references
        if opp_id:
            opp_stmt = select(Opportunity).where(Opportunity.id == opp_id)
            opp = (await session.execute(opp_stmt)).scalar_one_or_none()
            if opp:
                if not topic:
                    topic = opp.topic
                if opp.source_references:
                    sources.extend(opp.source_references)

        if not topic:
            topic = "General Technical Research"

        # Deterministic extraction grounded in source evidence
        packet_item = extract_research_packet(
            topic=topic,
            sources=sources,
            opportunity_id=opp_id,
            raw_text=engine_input.raw_text,
            context=engine_input.context,
            rules=self.rules,
        )

        if not dry_run:
            from app.repositories.research_repository import ResearchRepository

            repo = ResearchRepository(session)
            saved_packet = await repo.create_packet(packet_item.model_dump())
            await session.commit()
            packet_item.id = saved_packet.id

        self._last_packets[packet_item.id] = packet_item
        return packet_item

    async def run(
        self,
        context: EngineContext,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EngineResult:
        started_at = datetime.now(timezone.utc)
        payload = payload or {}
        dry_run = context.dry_run or payload.get("dry_run", False)

        try:
            engine_input = ResearchEngineInput(**payload)
        except Exception:
            engine_input = ResearchEngineInput(dry_run=dry_run)

        async with AsyncSessionLocal() as session:
            try:
                packet = await self.generate_packet(engine_input, session, dry_run=dry_run)
                ended_at = datetime.now(timezone.utc)
                duration_ms = int((ended_at - started_at).total_seconds() * 1000)

                verified_count = sum(1 for c in packet.claims if c.verification_status == "source-backed")
                uncertain_count = len(packet.uncertain_claims)
                avoid_count = len(packet.things_not_to_claim)

                res = EngineResult(
                    engine_id=self.id,
                    engine_version=self.version,
                    rules_version=self.rules_version,
                    project_id=context.project_id,
                    run_id=context.run_id,
                    success=True,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_ms=duration_ms,
                    input_count=len(packet.primary_sources) + len(packet.supporting_sources),
                    output_count=1,
                    rejected_count=0,
                    error_count=0,
                    cost=0.0,
                    data={
                        "packet_id": packet.id,
                        "topic": packet.topic,
                        "facts_count": len(packet.facts),
                        "numbers_count": len(packet.numbers),
                        "dates_count": len(packet.dates),
                        "entities_count": len(packet.entities),
                        "verified_claims_count": verified_count,
                        "uncertain_claims_count": uncertain_count,
                        "things_not_to_claim_count": avoid_count,
                        "contradictions_count": len(packet.contradictions),
                        "is_verified": packet.is_verified,
                    },
                )
                self._history[context.run_id] = res
                return res

            except Exception as e:
                ended_at = datetime.now(timezone.utc)
                duration_ms = int((ended_at - started_at).total_seconds() * 1000)
                err_res = EngineResult(
                    engine_id=self.id,
                    engine_version=self.version,
                    rules_version=self.rules_version,
                    project_id=context.project_id,
                    run_id=context.run_id,
                    success=False,
                    started_at=started_at,
                    ended_at=ended_at,
                    duration_ms=duration_ms,
                    input_count=0,
                    output_count=0,
                    rejected_count=0,
                    error_count=1,
                    cost=0.0,
                    error_message=str(e),
                    data={"error": str(e)},
                )
                self._history[context.run_id] = err_res
                return err_res

    async def dry_run(
        self,
        context: EngineContext,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EngineResult:
        context.dry_run = True
        return await self.run(context, payload)

    async def explain(
        self,
        context: EngineContext,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EngineExplanation:
        packet_id = (payload or {}).get("packet_id")
        packet = self._last_packets.get(packet_id) if packet_id else None

        if packet:
            backed_count = sum(1 for c in packet.claims if c.verification_status == "source-backed")
            uncertain_count = len(packet.uncertain_claims)
            summary_text = (
                f"Research Packet for '{packet.topic}' synthesized from "
                f"{len(packet.primary_sources)} primary and {len(packet.supporting_sources)} supporting citations. "
                f"Extracted {len(packet.facts)} facts, {len(packet.numbers)} metrics, {backed_count} source-backed claims, "
                f"{uncertain_count} uncertain claims, and {len(packet.things_not_to_claim)} things not to claim."
            )
            return EngineExplanation(
                run_id=context.run_id,
                engine_id=self.id,
                summary=summary_text,
                decisions=[
                    {
                        "action": "classify_claims",
                        "source_backed": backed_count,
                        "uncertain": uncertain_count,
                    },
                    {
                        "action": "flag_hype",
                        "unverified_vendor_claims_flagged": len(packet.things_not_to_claim),
                    },
                ],
                rules_fired=["claim_verification_requirements", "hype_patterns", "uncertainty_keywords"],
                data_lineage=[s.url for s in packet.primary_sources],
            )

        return EngineExplanation(
            run_id=context.run_id,
            engine_id=self.id,
            summary="Research Engine extracts traceable factual evidence, numbers, and dates while enforcing skepticism.",
            decisions=[],
            rules_fired=["claim_verification_requirements"],
            data_lineage=[],
        )
