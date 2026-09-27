import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evidence import (
    Claim,
    ClaimEvidence,
    Conclusion,
    ContentClaim,
    EvidenceSource,
    Experiment,
    ExperimentRun,
    Measurement,
)
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Claim]):
    """Storage boundary for provenance graphs, claims, citations, benchmarks, and coverage checks."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, claim_id: str) -> Optional[Claim]:
        return await self.get_claim_by_id(claim_id)

    # ---------------------------------------------------------
    # Sources
    # ---------------------------------------------------------
    async def create_source(
        self,
        url: str,
        title: str,
        domain: str,
        source_type: str = "primary",
        trust_weight: float = 1.0,
        author: Optional[str] = None,
        published_at: Optional[datetime] = None,
        raw_content: Optional[str] = None,
        packet_id: Optional[str] = None,
    ) -> EvidenceSource:
        source = EvidenceSource(
            id=str(uuid.uuid4()),
            packet_id=packet_id,
            url=url,
            title=title,
            domain=domain,
            source_type=source_type,
            trust_weight=trust_weight,
            author=author,
            published_at=published_at,
            raw_content=raw_content,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(source)
        await self.session.commit()
        return source

    async def record_citation(self, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compatible citation recording method for repository boundaries test."""
        url = evidence_data.get("url", "https://unknown.source")
        from urllib.parse import urlparse
        domain = urlparse(url).netloc or "unknown"
        title = evidence_data.get("title", url)
        src = await self.create_source(url=url, title=title, domain=domain)
        return {
            "id": src.id,
            "url": src.url,
            "fact": evidence_data.get("fact", ""),
            "title": src.title,
        }

    async def get_source_by_url(self, url: str) -> Optional[EvidenceSource]:
        stmt = select(EvidenceSource).where(EvidenceSource.url == url)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_source_by_id(self, source_id: str) -> Optional[EvidenceSource]:
        stmt = select(EvidenceSource).where(EvidenceSource.id == source_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_sources(self, packet_id: Optional[str] = None, limit: int = 100) -> List[EvidenceSource]:
        stmt = select(EvidenceSource).order_by(desc(EvidenceSource.created_at)).limit(limit)
        if packet_id:
            stmt = stmt.where(EvidenceSource.packet_id == packet_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # ---------------------------------------------------------
    # Claims
    # ---------------------------------------------------------
    async def create_claim(
        self,
        text: str,
        claim_type: str = "external_fact",
        confidence: float = 1.0,
        packet_id: Optional[str] = None,
        is_verified: bool = False,
    ) -> Claim:
        claim = Claim(
            id=str(uuid.uuid4()),
            packet_id=packet_id,
            text=text,
            claim_type=claim_type,
            confidence=confidence,
            is_verified=is_verified,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(claim)
        await self.session.commit()
        return claim

    async def get_claim_by_id(self, claim_id: str) -> Optional[Claim]:
        stmt = (
            select(Claim)
            .options(
                selectinload(Claim.evidence_links).selectinload(ClaimEvidence.source),
                selectinload(Claim.content_claims),
                selectinload(Claim.conclusions)
                .selectinload(Conclusion.experiment)
                .selectinload(Experiment.runs)
                .selectinload(ExperimentRun.measurements),
            )
            .where(Claim.id == claim_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_claims(
        self,
        packet_id: Optional[str] = None,
        claim_type: Optional[str] = None,
        is_verified: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Claim]:
        stmt = (
            select(Claim)
            .options(
                selectinload(Claim.evidence_links).selectinload(ClaimEvidence.source),
                selectinload(Claim.content_claims),
                selectinload(Claim.conclusions)
                .selectinload(Conclusion.experiment)
                .selectinload(Experiment.runs)
                .selectinload(ExperimentRun.measurements),
            )
            .order_by(desc(Claim.created_at))
            .limit(limit)
        )
        if packet_id:
            stmt = stmt.where(Claim.packet_id == packet_id)
        if claim_type:
            stmt = stmt.where(Claim.claim_type == claim_type)
        if is_verified is not None:
            stmt = stmt.where(Claim.is_verified == is_verified)

        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def link_evidence(
        self,
        claim_id: str,
        quote: str,
        source_id: Optional[str] = None,
        page_or_timestamp: Optional[str] = None,
        confidence: float = 0.9,
        notes: Optional[str] = None,
    ) -> ClaimEvidence:
        link = ClaimEvidence(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            source_id=source_id,
            quote=quote,
            page_or_timestamp=page_or_timestamp,
            confidence=confidence,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(link)

        # Mark claim verified if source is valid
        claim = await self.get_by_id(claim_id)
        if claim and claim.claim_type in ("external_fact", "original_measurement", "derived_conclusion"):
            claim.is_verified = True
            claim.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        return link

    async def label_opinion(
        self,
        claim_id: str,
        as_type: str = "opinion",  # opinion or prediction_speculation
    ) -> Optional[Claim]:
        claim = await self.get_by_id(claim_id)
        if not claim:
            return None
        claim.claim_type = as_type
        claim.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return claim

    # ---------------------------------------------------------
    # Experiments & Measurements
    # ---------------------------------------------------------
    async def create_experiment(
        self,
        title: str,
        hypothesis: str,
        method: str,
        opportunity_id: Optional[str] = None,
        tools_models: Optional[List[Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Experiment:
        experiment = Experiment(
            id=str(uuid.uuid4()),
            opportunity_id=opportunity_id,
            title=title,
            hypothesis=hypothesis,
            method=method,
            tools_models=tools_models or [],
            parameters=parameters or {},
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(experiment)
        await self.session.commit()
        return experiment

    async def get_experiment_by_id(self, experiment_id: str) -> Optional[Experiment]:
        stmt = (
            select(Experiment)
            .options(
                selectinload(Experiment.runs).selectinload(ExperimentRun.measurements),
                selectinload(Experiment.conclusions).selectinload(Conclusion.claim),
            )
            .where(Experiment.id == experiment_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_experiments(
        self,
        opportunity_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Experiment]:
        stmt = (
            select(Experiment)
            .options(
                selectinload(Experiment.runs).selectinload(ExperimentRun.measurements),
                selectinload(Experiment.conclusions).selectinload(Conclusion.claim),
            )
            .order_by(desc(Experiment.created_at))
            .limit(limit)
        )
        if opportunity_id:
            stmt = stmt.where(Experiment.opportunity_id == opportunity_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def add_experiment_run(
        self,
        experiment_id: str,
        run_number: int = 1,
        execution_time_ms: int = 0,
        cost_usd: float = 0.0,
        status: str = "success",
        error_message: Optional[str] = None,
        artifacts: Optional[List[Any]] = None,
        measurements: Optional[List[Dict[str, Any]]] = None,
    ) -> ExperimentRun:
        run = ExperimentRun(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            run_number=run_number,
            execution_time_ms=execution_time_ms,
            cost_usd=cost_usd,
            status=status,
            error_message=error_message,
            artifacts=artifacts or [],
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(run)
        await self.session.commit()

        if measurements:
            for m in measurements:
                meas = Measurement(
                    id=str(uuid.uuid4()),
                    run_id=run.id,
                    metric=m["metric"],
                    value=float(m["value"]),
                    unit=m.get("unit"),
                    context=m.get("context"),
                    sample_size=int(m.get("sample_size", 1)),
                    created_at=datetime.now(timezone.utc),
                )
                self.session.add(meas)
            await self.session.commit()

        return run

    async def add_conclusion(
        self,
        experiment_id: str,
        summary: str,
        claim_id: Optional[str] = None,
        confidence: float = 0.95,
    ) -> Conclusion:
        conclusion = Conclusion(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            summary=summary,
            claim_id=claim_id,
            confidence=confidence,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(conclusion)

        # If linked to a claim, verify that claim as original_measurement or derived_conclusion
        if claim_id:
            claim = await self.get_by_id(claim_id)
            if claim:
                claim.is_verified = True
                if claim.claim_type not in ("original_measurement", "derived_conclusion"):
                    claim.claim_type = "derived_conclusion"
                claim.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        return conclusion

    # ---------------------------------------------------------
    # Content Claims & Script Mapping
    # ---------------------------------------------------------
    async def create_content_claim(
        self,
        claim_id: str,
        content_id: str,
        quote_in_script: str,
        section_id: str = "evidence",
        verification_status: str = "unsupported",
    ) -> ContentClaim:
        # Check if the underlying claim is verified or opinion
        claim = await self.get_by_id(claim_id)
        status = verification_status
        if claim:
            if claim.claim_type in ("opinion", "prediction_speculation"):
                status = "labeled_opinion"
            elif claim.is_verified:
                status = "verified"

        content_claim = ContentClaim(
            id=str(uuid.uuid4()),
            claim_id=claim_id,
            content_id=content_id,
            section_id=section_id,
            quote_in_script=quote_in_script,
            verification_status=status,
            is_overridden=False,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(content_claim)
        await self.session.commit()
        return content_claim

    async def override_content_claim(
        self,
        content_claim_id: str,
        reason: str,
    ) -> Optional[ContentClaim]:
        stmt = select(ContentClaim).where(ContentClaim.id == content_claim_id)
        res = await self.session.execute(stmt)
        cc = res.scalar_one_or_none()
        if not cc:
            return None
        cc.is_overridden = True
        cc.override_reason = reason
        cc.verification_status = "overridden"
        await self.session.commit()
        return cc

    async def list_content_claims(self, content_id: str) -> List[ContentClaim]:
        stmt = (
            select(ContentClaim)
            .options(
                selectinload(ContentClaim.claim)
                .selectinload(Claim.evidence_links)
                .selectinload(ClaimEvidence.source)
            )
            .where(ContentClaim.content_id == content_id)
            .order_by(ContentClaim.created_at)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # ---------------------------------------------------------
    # Provenance Graph & Coverage Analysis
    # ---------------------------------------------------------
    async def trace_provenance(self, claim_id: str) -> Dict[str, Any]:
        """Traverse graph: Source -> Claim -> Experiment / Measurement -> Conclusion -> Script Section."""
        claim = await self.get_claim_by_id(claim_id)
        if not claim:
            return {"error": f"Claim {claim_id} not found."}

        sources = []
        for link in claim.evidence_links:
            src = link.source
            sources.append({
                "source_id": src.id if src else None,
                "url": src.url if src else None,
                "title": src.title if src else None,
                "domain": src.domain if src else None,
                "source_type": src.source_type if src else "supporting",
                "trust_weight": src.trust_weight if src else 1.0,
                "quote": link.quote,
                "confidence": link.confidence,
            })

        experiments = []
        for conclusion in claim.conclusions:
            exp = conclusion.experiment
            if exp:
                runs_data = []
                for run in exp.runs:
                    runs_data.append({
                        "run_id": run.id,
                        "run_number": run.run_number,
                        "cost_usd": run.cost_usd,
                        "execution_time_ms": run.execution_time_ms,
                        "status": run.status,
                        "measurements": [
                            {
                                "metric": m.metric,
                                "value": m.value,
                                "unit": m.unit,
                                "context": m.context,
                            }
                            for m in run.measurements
                        ],
                    })
                experiments.append({
                    "experiment_id": exp.id,
                    "title": exp.title,
                    "hypothesis": exp.hypothesis,
                    "method": exp.method,
                    "conclusion_summary": conclusion.summary,
                    "confidence": conclusion.confidence,
                    "runs": runs_data,
                })

        content_usages = [
            {
                "content_claim_id": cc.id,
                "content_id": cc.content_id,
                "section_id": cc.section_id,
                "quote_in_script": cc.quote_in_script,
                "verification_status": cc.verification_status,
                "is_overridden": cc.is_overridden,
                "override_reason": cc.override_reason,
            }
            for cc in claim.content_claims
        ]

        return {
            "claim_id": claim.id,
            "claim_text": claim.text,
            "claim_type": claim.claim_type,
            "is_verified": claim.is_verified,
            "confidence": claim.confidence,
            "sources": sources,
            "experiments": experiments,
            "content_usages": content_usages,
        }

    async def calculate_coverage(
        self,
        claims: Optional[List[Claim]] = None,
        packet_id: Optional[str] = None,
        content_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute full evidence coverage statistics and quality gate evaluation."""
        if claims is None:
            if content_id:
                content_claims = await self.list_content_claims(content_id)
                claim_ids = [cc.claim_id for cc in content_claims]
                if claim_ids:
                    stmt = (
                        select(Claim)
                        .options(
                            selectinload(Claim.evidence_links).selectinload(ClaimEvidence.source),
                            selectinload(Claim.conclusions),
                            selectinload(Claim.content_claims),
                        )
                        .where(Claim.id.in_(claim_ids))
                    )
                    res = await self.session.execute(stmt)
                    claims = list(res.scalars().all())
                else:
                    claims = []
            elif packet_id:
                claims = await self.list_claims(packet_id=packet_id, limit=200)
            else:
                claims = await self.list_claims(limit=200)

        total_claims = len(claims)
        factual_claims = 0
        primary_source_backed = 0
        supporting_source_backed = 0
        original_test_backed = 0
        unsupported = 0
        opinions_labeled = 0
        overridden = 0

        for c in claims:
            # Check opinion / speculation
            if c.claim_type in ("opinion", "prediction_speculation"):
                opinions_labeled += 1
                continue

            factual_claims += 1

            # Check override status on any linked content_claim
            has_override = any(cc.is_overridden for cc in c.content_claims)
            if has_override:
                overridden += 1

            # Check original test
            has_experiment = len(c.conclusions) > 0 or c.claim_type == "original_measurement"
            if has_experiment:
                original_test_backed += 1
                continue

            # Check source backing
            primary_links = [l for l in c.evidence_links if l.source and l.source.source_type == "primary"]
            supporting_links = [l for l in c.evidence_links if l.source and l.source.source_type != "primary"]

            if primary_links:
                primary_source_backed += 1
            elif supporting_links:
                supporting_source_backed += 1
            elif not has_override:
                unsupported += 1

        verified_backed = primary_source_backed + supporting_source_backed + original_test_backed + overridden
        coverage_percent = round((verified_backed / factual_claims * 100), 1) if factual_claims > 0 else 100.0
        gate_passed = (unsupported == 0) and (coverage_percent >= 85.0)

        return {
            "total_claims": total_claims,
            "factual_claims": factual_claims,
            "primary_source_backed": primary_source_backed,
            "supporting_source_backed": supporting_source_backed,
            "original_test_backed": original_test_backed,
            "opinions_labeled": opinions_labeled,
            "overridden_count": overridden,
            "unsupported": unsupported,
            "coverage_percent": coverage_percent,
            "gate_passed": gate_passed,
        }
